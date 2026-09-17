"""Decision-making summary — status, grand totals, per-place rollups.

Pure functions. No UI, no I/O. Used by both the web Summary tab and the
PDF exporter, so the two stay in sync.

Pass 2 changes (items 10, 11, 20):
  - Adds `structured_flags` — a machine-readable list of decision flags
    that the UI can render as clickable cards with modals.
  - Keeps the legacy `flags: list[str]` for PDF export compatibility.
  - All display text uses "assistant(s)", never "helper(s)".
"""
from __future__ import annotations

from core.normalize import to_float


def _grade_tone(score: int) -> str:
    if score >= 70:
        return "primary"
    if score >= 55:
        return "warning"
    return "danger"


def compute(rpt) -> dict:
    from core.quality import compute_quality
    q = compute_quality(rpt)

    # ── Per-building rollup ────────────────────────────────────────────
    bb: dict[str, dict] = {}
    for r in rpt.work_progress:
        b = (r.get("building") or "—").strip() or "—"
        e = bb.setdefault(b, {
            "floors": set(), "activities": set(),
            "crew": 0, "rows": 0, "top_counts": {},
            "skilled": 0, "assistants": 0,
            "rows_list": [],
        })
        fl = (r.get("floor") or "").strip()
        if fl:
            e["floors"].add(fl)
        a = (r.get("activity") or "").strip()
        if a:
            e["activities"].add(a)
            e["top_counts"][a] = e["top_counts"].get(a, 0) + 1
        sk = int(to_float(r.get("skilled")) or 0)
        hp = int(to_float(r.get("helpers")) or 0)  # field name unchanged
        e["skilled"]    += sk
        e["assistants"] += hp
        e["crew"]       += sk + hp
        e["rows"]       += 1
        e["rows_list"].append(r)

    buildings = []
    for b, e in bb.items():
        top = "—"
        if e["top_counts"]:
            top = max(e["top_counts"].items(), key=lambda kv: kv[1])[0]
        buildings.append({
            "building": b,
            "floors": len(e["floors"]),
            "activities": len(e["activities"]),
            "rows": e["rows"],
            "crew": e["crew"],
            "skilled": e["skilled"],
            "assistants": e["assistants"],
            "top_activity": top,
        })
    buildings.sort(key=lambda x: (-x["crew"], x["building"]))

    # ── Per-activity rollup ────────────────────────────────────────────
    aa: dict[str, dict] = {}
    for r in rpt.work_progress:
        a = (r.get("activity") or "").strip()
        if not a:
            continue
        e = aa.setdefault(a, {"rows": 0, "crew": 0, "buildings": set()})
        e["rows"] += 1
        e["crew"] += int(to_float(r.get("skilled")) or 0) \
                     + int(to_float(r.get("helpers")) or 0)
        b = (r.get("building") or "").strip()
        if b:
            e["buildings"].add(b)

    activities = []
    for a, e in aa.items():
        activities.append({
            "activity": a,
            "rows": e["rows"],
            "crew": e["crew"],
            "buildings": len(e["buildings"]),
        })
    activities.sort(key=lambda x: (-x["crew"], x["activity"]))

    # ── Totals ─────────────────────────────────────────────────────────
    sk = hp = 0
    for r in rpt.work_progress:
        sk += int(to_float(r.get("skilled")) or 0)
        hp += int(to_float(r.get("helpers")) or 0)
    total_crew = sk + hp

    prog_vals = [to_float(r.get("progress_pct")) for r in rpt.work_progress]
    prog_vals = [v for v in prog_vals if v is not None]
    avg_prog = (sum(prog_vals) / len(prog_vals)) if prog_vals else 0.0

    # ── Status / decision flags ────────────────────────────────────────
    hard_conflicts = [c for c in rpt.conflicts
                      if c.get("severity") == "hard"]
    soft_conflicts = [c for c in rpt.conflicts
                      if c.get("severity") == "soft"]
    low_conf_rows  = [r for r in rpt.work_progress
                      if r.get("confidence") == "low"]

    n_hard = len(hard_conflicts)
    n_soft = len(soft_conflicts)
    n_low_conf = len(low_conf_rows)

    if n_hard > 0 or q.score < 55:
        status, label = "at_risk", "AT RISK"
        detail = ("Hard conflicts or low data quality — engineer "
                  "review required before export.")
    elif n_soft > 3 or q.score < 70 or n_low_conf > 0:
        status, label = "attention", "NEEDS ATTENTION"
        detail = ("Minor issues detected — verify flagged items "
                  "before sign-off.")
    else:
        status, label = "on_track", "ON TRACK"
        detail = "Clean data, no hard conflicts. Ready for export."

    # ── Legacy plain-text flags (kept for the PDF exporter) ────────────
    flags: list[str] = []
    if n_hard:
        flags.append(f"{n_hard} hard conflict(s) — sources disagree; "
                     f"review required before export.")
    if n_soft:
        flags.append(f"{n_soft} soft conflict(s) auto-resolved within "
                     f"tolerance.")
    if n_low_conf:
        flags.append(f"{n_low_conf} low-confidence row(s) — verify "
                     f"against source.")
    if q.score < 70:
        flags.append(f"Data quality score {q.score}/100 — below the "
                     f"recommended threshold of 70.")
    if not rpt.hse_observations:
        flags.append("No HSE observations recorded — confirm this is "
                     "not an oversight.")
    if total_crew == 0 and rpt.work_progress:
        flags.append("No crew headcounts extracted — check source "
                     "content.")

    # ── Structured flags for the interactive UI (items 10, 11) ─────────
    structured: list[dict] = []
    if hard_conflicts:
        structured.append({
            "kind": "hard_conflicts",
            "count": len(hard_conflicts),
            "label": (f"{len(hard_conflicts)} of your uploaded files "
                      f"gave different values for the same field"),
            "conflicts": hard_conflicts,
        })
    if low_conf_rows:
        structured.append({
            "kind": "unify_headers",
            "count": len(low_conf_rows),
            "label": "Some headers should be unified",
            "rows": low_conf_rows,
        })
    structured.append({
        "kind": "quality_score",
        "score": q.score,
        "label": f"Data Quality is {q.score}%",
    })
    extra_info: list[str] = []
    if n_soft:
        extra_info.append(f"{n_soft} soft conflict(s) auto-resolved "
                          f"within tolerance.")
    if not rpt.hse_observations:
        extra_info.append("No HSE observations recorded — confirm this "
                          "is not an oversight.")
    if total_crew == 0 and rpt.work_progress:
        extra_info.append("No crew headcounts extracted — check source "
                          "content.")
    if extra_info:
        structured.append({"kind": "info", "items": extra_info})

    # ── Executive summary ──────────────────────────────────────────────
    parts: list[str] = []
    if buildings:
        top_b = buildings[0]
        parts.append(
            f"{len(buildings)} building(s) active, "
            f"Building {top_b['building']} carrying the largest crew "
            f"({top_b['crew']})."
        )
    parts.append(
        f"Total manpower on site: {total_crew} "
        f"({sk} skilled · {hp} assistants)."
    )
    if prog_vals:
        parts.append(f"Average reported progress: {avg_prog:.0f}%.")
    if activities:
        parts.append(
            f"Most deployed trade: {activities[0]['activity']} "
            f"({activities[0]['rows']} location(s))."
        )
    exec_summary = " ".join(parts)

    return {
        "status": status,
        "status_label": label,
        "status_detail": detail,
        "quality": q,
        "grade_tone": _grade_tone(q.score),
        "skilled": sk,
        "helpers": hp,            # field name kept for compatibility
        "assistants": hp,         # new display alias
        "total_crew": total_crew,
        "total_rows": len(rpt.work_progress),
        "total_buildings": len(buildings),
        "total_activities": len(activities),
        "avg_progress": avg_prog,
        "n_hard": n_hard,
        "n_soft": n_soft,
        "n_low_conf": n_low_conf,
        "buildings": buildings,
        "activities": activities,
        "flags": flags,                    # legacy, PDF-compatible
        "structured_flags": structured,    # new, UI-driven
        "exec_summary": exec_summary,
    }
