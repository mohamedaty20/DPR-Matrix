"""Zone Progress Board — derived from the current report, not user input.

Each zone (= building, or zone field if present) gets:
  · an inferred construction stage from its activities
  · a crew count, floor count, activity list, progress avg
  · a professional colour-coded card in the site map

Below the map, a narrative summary explains what is happening on site
and what a project engineer should act on.
"""
from __future__ import annotations

from collections import Counter

from nicegui import ui

from core.normalize import to_float
from ui import state
from ui.shell import page_shell


# ═══════════════════════════════════════════════════════════════════════════
# Stage vocabulary
# ═══════════════════════════════════════════════════════════════════════════
STAGES: list[tuple[str, str, str]] = [
    ("not_started",   "Not Started",   "#4f4f56"),
    ("excavation",    "Excavation",    "#d4a017"),
    ("blinding",      "Blinding",      "#4a80c4"),
    ("reinforcement", "Reinforcement", "#9a9aa0"),
    ("formwork",      "Formwork",      "#c47a3b"),
    ("pouring",       "Pouring",       "#F2740C"),
    ("curing",        "Curing",        "#8a4ab0"),
    ("finishing",     "Finishing",     "#b06b3a"),
    ("complete",      "Complete",      "#0a8a3b"),
]

_ORDER = {k: i for i, (k, _, _) in enumerate(STAGES)}
_LABEL = {k: l for k, l, _ in STAGES}
_COLOR = {k: c for k, _, c in STAGES}

# Activity → stage. Lowercase substrings matched against normalised
# activity names from the aggregator.
_ACTIVITY_TO_STAGE = {
    "excavation":       "excavation",
    "backfilling":      "excavation",
    "blinding":         "blinding",
    "steel fixing":     "reinforcement",
    "reinforcement":    "reinforcement",
    "formwork":         "formwork",
    "concrete works":   "pouring",
    "concreting":       "pouring",
    "curing":           "curing",
    "waterproofing":    "finishing",
    "mortar works":     "finishing",
    "brickworks":       "finishing",
    "plastering":       "finishing",
    "sealer works":     "finishing",
    "painting":         "finishing",
    "tiling":           "finishing",
    "gypsum works":     "finishing",
    "ceiling works":    "finishing",
    "carpentry":        "finishing",
    "electrical":       "finishing",
    "plumbing":         "finishing",
}


def _stage_for_activity(activity: str) -> str | None:
    a = (activity or "").lower().strip()
    if not a:
        return None
    # direct hit
    if a in _ACTIVITY_TO_STAGE:
        return _ACTIVITY_TO_STAGE[a]
    # substring
    for k, v in _ACTIVITY_TO_STAGE.items():
        if k in a:
            return v
    return None


def _floor_sort(s: str) -> tuple:
    try:
        return (0, int(s))
    except (ValueError, TypeError):
        return (1, s)


# ═══════════════════════════════════════════════════════════════════════════
# Zone derivation
# ═══════════════════════════════════════════════════════════════════════════
def _derive_zones(rpt) -> list[dict]:
    groups: dict[str, dict] = {}

    for r in rpt.work_progress:
        b = (r.get("building") or "").strip()
        z = (r.get("zone") or "").strip()
        key = z or (f"Building {b}" if b else "Unassigned")

        g = groups.setdefault(key, {
            "id": key,
            "building": b,
            "floors": set(),
            "rows": 0,
            "activities": {},
            "crew": 0,
            "conf_bad": 0,
            "conf_total": 0,
            "progress_sum": 0.0,
            "progress_n": 0,
        })

        fl = (r.get("floor") or "").strip()
        if fl:
            g["floors"].add(fl)
        g["rows"] += 1

        a = (r.get("activity") or "").strip()
        if a:
            g["activities"][a] = g["activities"].get(a, 0) + 1

        sk = to_float(r.get("skilled")) or 0
        hp = to_float(r.get("helpers")) or 0
        g["crew"] += int(sk + hp)

        c = r.get("confidence", "low")
        g["conf_total"] += 1
        if c == "low":
            g["conf_bad"] += 1

        p = to_float(r.get("progress_pct"))
        if p is not None:
            g["progress_sum"] += p
            g["progress_n"] += 1

    out = []
    for key, g in groups.items():
        stage = _infer_stage(
            g["activities"], g["progress_sum"], g["progress_n"],
        )
        avg_prog = (
            g["progress_sum"] / g["progress_n"]
            if g["progress_n"] else None
        )
        top_activity = ""
        if g["activities"]:
            top_activity = max(
                g["activities"].items(), key=lambda kv: kv[1],
            )[0]

        out.append({
            "id": g["id"],
            "building": g["building"],
            "floors": sorted(g["floors"], key=_floor_sort),
            "rows": g["rows"],
            "activities": g["activities"],
            "top_activity": top_activity,
            "crew": g["crew"],
            "stage": stage,
            "avg_progress": avg_prog,
            "low_conf": g["conf_bad"],
        })

    out.sort(key=lambda x: (-x["crew"], x["id"]))
    return out


def _infer_stage(activities: dict, prog_sum: float, prog_n: int) -> str:
    advanced = -1
    for act in activities:
        st = _stage_for_activity(act)
        if st:
            advanced = max(advanced, _ORDER[st])
    if advanced >= 0:
        for k, v in _ORDER.items():
            if v == advanced:
                return k
    # Fallback to average progress
    if prog_n == 0:
        return "not_started"
    avg = prog_sum / prog_n
    if avg >= 95:
        return "complete"
    if avg >= 70:
        return "finishing"
    if avg >= 40:
        return "pouring"
    if avg > 0:
        return "excavation"
    return "not_started"


# ═══════════════════════════════════════════════════════════════════════════
# Page CSS
# ═══════════════════════════════════════════════════════════════════════════
_ZONES_CSS = """
<style>
.dpr-z-stage-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 14px;
  background: linear-gradient(180deg, #0c0c0f 0%, #08080a 100%);
  border: 1px solid rgba(242,116,12,0.20);
  border-radius: 12px;
  margin-bottom: 14px;
}
.dpr-z-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  background: #0c0c0f;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}
.dpr-z-pill-dot {
  width: 8px; height: 8px; border-radius: 3px;
  display: inline-block;
}
.dpr-z-pill-count {
  color: #e8e8ea;
  font-weight: 700;
}
.dpr-z-pill-label {
  color: #85858c;
  text-transform: uppercase;
  font-size: 9.5px;
  letter-spacing: 0.08em;
}

.dpr-z-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
  width: 100%;
  margin-bottom: 18px;
}
.dpr-z-card {
  background: linear-gradient(180deg, #121216 0%, #08080a 100%);
  border: 1px solid rgba(242,116,12,0.20);
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: border-color .12s ease, transform .12s ease;
}
.dpr-z-card:hover {
  border-color: rgba(242,116,12,0.5);
  transform: translateY(-1px);
}
.dpr-z-band {
  padding: 8px 12px;
  color: #050506;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.dpr-z-band-num {
  font-size: 12px;
  letter-spacing: 0;
  text-transform: none;
  font-weight: 700;
}
.dpr-z-body {
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.dpr-z-id {
  color: #e8e8ea;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: -0.005em;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dpr-z-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.dpr-z-tag {
  font-size: 10px;
  font-weight: 600;
  color: #85858c;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  padding: 2px 7px;
  border-radius: 4px;
  letter-spacing: 0.02em;
}
.dpr-z-tag b { color: #e8e8ea; font-weight: 700; }
.dpr-z-prog-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}
.dpr-z-prog {
  flex: 1;
  height: 6px;
  background: rgba(255,255,255,0.05);
  border-radius: 999px;
  overflow: hidden;
}
.dpr-z-prog-fill {
  height: 100%;
  border-radius: 999px;
  transition: width .3s ease;
}
.dpr-z-prog-val {
  color: #c8c8cc;
  font-size: 10.5px;
  font-weight: 700;
  white-space: nowrap;
}
.dpr-z-prog-val.muted { color: #4f4f56; font-weight: 400; }
.dpr-z-top {
  color: #85858c;
  font-size: 11px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dpr-z-top b { color: #e8e8ea; font-weight: 600; }

/* ── Narrative ───────────────────────────────────────────────── */
.dpr-z-narr {
  background: linear-gradient(180deg, #0c0c0f 0%, #08080a 100%);
  border: 1px solid rgba(242,116,12,0.20);
  border-radius: 12px;
  padding: 20px 22px;
  margin-bottom: 14px;
}
.dpr-z-narr-title {
  color: #F2740C;
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-weight: 700;
  margin-bottom: 6px;
}
.dpr-z-narr-sub {
  color: #4f4f56;
  font-size: 11px;
  line-height: 1.5;
  margin-bottom: 18px;
}
.dpr-z-block {
  margin-bottom: 18px;
}
.dpr-z-block:last-child { margin-bottom: 0; }
.dpr-z-block-head {
  color: #e8e8ea;
  font-size: 12.5px;
  font-weight: 700;
  letter-spacing: 0.02em;
  margin-bottom: 8px;
  padding-bottom: 5px;
  border-bottom: 1px solid rgba(242,116,12,0.10);
}
.dpr-z-block-body {
  color: #c8c8cc;
  font-size: 12px;
  line-height: 1.65;
}
.dpr-z-block-body p { margin: 0 0 8px 0; }
.dpr-z-block-body ul {
  margin: 0;
  padding-left: 18px;
  list-style: none;
}
.dpr-z-block-body li {
  position: relative;
  padding-left: 6px;
  margin-bottom: 5px;
  line-height: 1.55;
}
.dpr-z-block-body li:before {
  content: "▸";
  position: absolute;
  left: -14px;
  color: #F2740C;
  font-size: 11px;
}
.dpr-z-flag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-right: 6px;
  margin-bottom: 4px;
}
.dpr-z-flag-warn { background: rgba(255,176,32,0.10); color: #ffb020; border: 1px solid rgba(255,176,32,0.35); }
.dpr-z-flag-ok   { background: rgba(10,138,59,0.10); color: #0a8a3b; border: 1px solid rgba(10,138,59,0.35); }
.dpr-z-flag-risk { background: rgba(255,77,106,0.10); color: #ff4d6a; border: 1px solid rgba(255,77,106,0.35); }
</style>
"""


# ═══════════════════════════════════════════════════════════════════════════
# Narrative builder
# ═══════════════════════════════════════════════════════════════════════════
def _build_narrative(zones: list[dict], rpt) -> dict:
    total_zones = len(zones)
    total_crew = sum(z["crew"] for z in zones)
    total_rows = sum(z["rows"] for z in zones)
    total_activities = len({
        a for z in zones for a in z["activities"].keys()
    })

    stage_counts = Counter(z["stage"] for z in zones)

    # Order zones by stage progression
    sorted_stage = sorted(zones, key=lambda z: _ORDER.get(z["stage"], 0))
    earliest = sorted_stage[0] if sorted_stage else None
    latest = sorted_stage[-1] if sorted_stage else None

    # Crew concentration
    sorted_crew = sorted(zones, key=lambda z: -z["crew"])
    top_crew = [z for z in sorted_crew if z["crew"] > 0][:3]

    # Activity concentration across the site
    act_counter: Counter = Counter()
    for z in zones:
        for a, c in z["activities"].items():
            act_counter[a] += c
    top_activities = act_counter.most_common(5)

    # Zones requiring attention
    stalled: list[dict] = []
    high_crew_low_prog: list[dict] = []
    low_conf_zones: list[dict] = []

    for z in zones:
        if z["low_conf"] > 0:
            low_conf_zones.append(z)
        if z["stage"] in ("not_started", "excavation") and z["crew"] > 0:
            stalled.append(z)
        if (z["crew"] >= 10
                and z["avg_progress"] is not None
                and z["avg_progress"] < 40):
            high_crew_low_prog.append(z)

    # ── Paragraph 1: Site status ─────────────────────────────────────
    if total_zones == 0:
        p1 = "No zones are active in the current report."
    else:
        top_stage_key, top_stage_count = (
            stage_counts.most_common(1)[0] if stage_counts else ("not_started", 0)
        )
        p1 = (
            f"Across {total_zones} active zone(s), the site is "
            f"predominantly in the {_LABEL[top_stage_key]} stage "
            f"({top_stage_count} zone(s)). "
            f"Total on-site manpower is {total_crew} across "
            f"{total_rows} reported work rows spanning "
            f"{total_activities} distinct activities. "
        )
        if latest and earliest and latest is not earliest:
            p1 += (
                f"The most advanced work is at {latest['id']} "
                f"({_LABEL[latest['stage']]}), while {earliest['id']} "
                f"remains at {_LABEL[earliest['stage']]}. "
            )
        if total_crew == 0:
            p1 += "No crew headcounts were extracted — verify the source reports."

    # ── Paragraph 2: Crew concentration ──────────────────────────────
    if total_crew == 0:
        p2 = "Manpower data is not available."
    elif not top_crew:
        p2 = "No crew distribution could be derived from the current data."
    else:
        bits = []
        for z in top_crew:
            pct = z["crew"] / total_crew * 100
            bits.append(f"{z['id']} ({z['crew']}, {pct:.0f}%)")
        p2 = (
            f"Manpower is concentrated in "
            f"{', '.join(bits[:-1]) + ' and ' + bits[-1] if len(bits) > 1 else bits[0]}. "
        )
        combined = sum(z["crew"] for z in top_crew) / total_crew * 100
        if combined >= 60:
            p2 += (
                f"Together these zones hold {combined:.0f}% of the site crew — "
                f"a heavy work front that will drive near-term progress but "
                f"may leave other areas under-resourced."
            )
        elif combined >= 40:
            p2 += (
                f"These account for {combined:.0f}% of total crew, "
                f"indicating a reasonably distributed workforce with a "
                f"clear primary work front."
            )
        else:
            p2 += (
                f"Crew is well distributed — no single zone dominates, "
                f"which reduces single-point-of-failure risk."
            )

    # ── Activity concentration ───────────────────────────────────────
    activity_bullets: list[str] = []
    for act, count in top_activities:
        zones_with = [z["id"] for z in zones if act in z["activities"]]
        activity_bullets.append(
            f"<b>{act}</b> — {count} location(s) across "
            f"{len(zones_with)} zone(s): {', '.join(zones_with[:4])}"
            + (" …" if len(zones_with) > 4 else "")
        )

    # ── Attention bullets ────────────────────────────────────────────
    attention: list[str] = []
    if stalled:
        names = ", ".join(z["id"] for z in stalled[:5])
        attention.append(
            f"<b>{len(stalled)} zone(s)</b> still at excavation or not-started "
            f"despite having crew assigned — possible schedule slippage: {names}."
        )
    if high_crew_low_prog:
        names = ", ".join(
            f"{z['id']} ({z['crew']} crew, "
            f"{z['avg_progress']:.0f}% progress)"
            for z in high_crew_low_prog[:5]
        )
        attention.append(
            f"<b>High crew, low progress</b> — resources may be mis-allocated: "
            f"{names}."
        )
    if low_conf_zones:
        names = ", ".join(z["id"] for z in low_conf_zones[:6])
        attention.append(
            f"<b>{len(low_conf_zones)} zone(s)</b> contain low-confidence rows "
            f"— verify against source files before sign-off: {names}."
        )
    n_hard = sum(1 for c in rpt.conflicts if c.get("severity") == "hard")
    if n_hard:
        attention.append(
            f"<b>{n_hard} hard conflict(s)</b> detected across source files — "
            f"see the Conflicts banner on the Report dashboard."
        )
    if not attention:
        attention.append(
            "No material issues detected. Data is consistent and zone "
            "progression is logical across the site."
        )

    # ── Recommendations ──────────────────────────────────────────────
    recs: list[str] = []
    if stalled:
        recs.append(
            f"Reallocate crew to accelerate {', '.join(z['id'] for z in stalled[:3])} "
            f"or confirm the delay is contractual."
        )
    if high_crew_low_prog:
        top = high_crew_low_prog[0]
        recs.append(
            f"Audit productivity in {top['id']} — {top['crew']} crew at "
            f"{top['avg_progress']:.0f}% suggests a bottleneck or idle time."
        )
    if low_conf_zones:
        recs.append(
            "Open the Reconcile Sources page and verify the flagged zones "
            "before including them in exports."
        )
    if total_crew > 0 and total_zones > 0:
        avg_per_zone = total_crew / total_zones
        if avg_per_zone < 5:
            recs.append(
                f"Average crew per zone is {avg_per_zone:.1f} — "
                f"review whether the workforce on site matches plan."
            )
        elif avg_per_zone > 20:
            recs.append(
                f"Average crew per zone is {avg_per_zone:.1f} — "
                f"consider whether supervision coverage is adequate."
            )
    if latest and _ORDER[latest["stage"]] >= _ORDER["pouring"]:
        recs.append(
            f"Schedule concrete cube tests and curing verification for "
            f"{latest['id']} in line with standard compliance practice."
        )
    if not recs:
        recs.append("Continue as planned — no corrective action required today.")

    return {
        "p1": p1,
        "p2": p2,
        "activity_bullets": activity_bullets,
        "attention": attention,
        "recs": recs,
        "stage_counts": stage_counts,
        "total_zones": total_zones,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Render
# ═══════════════════════════════════════════════════════════════════════════
def render():
    with page_shell(
        active="zones",
        title="Zone Progress Board",
        subtitle=(
            "Site map derived from the current report's work rows. "
            "Stage is inferred from activities; crew and progress come "
            "straight from the aggregated data."
        ),
    ):
        ui.add_head_html(_ZONES_CSS, shared=False)

        rpt = state.report()
        if rpt is None:
            with ui.card().classes("dpr-card w-full"):
                ui.label("No report in this session.").classes("dpr-title text-xl")
                ui.label(
                    "Aggregate at least one file first — the board is "
                    "derived from the report's work progress rows."
                ).classes("text-white")
            with ui.row().classes("gap-3 mt-2"):
                ui.button("Back to Upload",
                          on_click=lambda: ui.navigate.to("/"))
            return

        zones = _derive_zones(rpt)
        if not zones:
            ui.html(
                '<div class="dpr-z-narr" style="text-align:center;padding:40px;">'
                '<div style="color:#85858c;font-size:13px;">'
                'No zones detected. The current report contains no work '
                'progress rows with building or zone information.'
                '</div></div>'
            )
            return

        # ── Stage distribution strip ─────────────────────────────────
        stage_counts = Counter(z["stage"] for z in zones)
        pills = ""
        for key, label, color in STAGES:
            count = stage_counts.get(key, 0)
            if count == 0:
                continue
            pills += (
                f'<span class="dpr-z-pill">'
                f'  <span class="dpr-z-pill-dot" '
                f'        style="background:{color};"></span>'
                f'  <span class="dpr-z-pill-count">{count}</span>'
                f'  <span class="dpr-z-pill-label">{label}</span>'
                f'</span>'
            )
        ui.html(
            f'<div class="dpr-z-stage-strip">'
            f'  <span style="color:#85858c;font-size:10.5px;'
            f'      letter-spacing:0.12em;text-transform:uppercase;'
            f'      font-weight:600;align-self:center;margin-right:6px;">'
            f'    Stage distribution · {len(zones)} zone(s)'
            f'  </span>'
            f'  {pills}'
            f'</div>'
        )

        # ── Site map grid ────────────────────────────────────────────
        cards = ""
        for z in zones:
            color = _COLOR.get(z["stage"], "#4f4f56")
            label = _LABEL.get(z["stage"], z["stage"])

            floors_txt = (
                f"{len(z['floors'])} floor(s)" if z["floors"] else "—"
            )
            prog_val = z["avg_progress"]
            if prog_val is None:
                prog_html = (
                    '<span class="dpr-z-prog-val muted">no progress data</span>'
                )
                bar_html = ""
            else:
                pct = max(0.0, min(100.0, prog_val))
                bar_html = (
                    f'<div class="dpr-z-prog">'
                    f'  <div class="dpr-z-prog-fill" '
                    f'       style="width:{pct:.0f}%;background:{color};"></div>'
                    f'</div>'
                )
                prog_html = f'<span class="dpr-z-prog-val">{pct:.0f}%</span>'

            top = z["top_activity"] or "—"

            cards += (
                f'<div class="dpr-z-card">'
                f'  <div class="dpr-z-band" style="background:{color};">'
                f'    <span>{label}</span>'
                f'    <span class="dpr-z-band-num">{z["crew"]} crew</span>'
                f'  </div>'
                f'  <div class="dpr-z-body">'
                f'    <div class="dpr-z-id">{z["id"]}</div>'
                f'    <div class="dpr-z-meta">'
                f'      <span class="dpr-z-tag"><b>{floors_txt}</b></span>'
                f'      <span class="dpr-z-tag"><b>{z["rows"]}</b> rows</span>'
                f'      <span class="dpr-z-tag"><b>{len(z["activities"])}</b> act.</span>'
                f'    </div>'
                f'    <div class="dpr-z-prog-wrap">'
                f'      {bar_html}{prog_html}'
                f'    </div>'
                f'    <div class="dpr-z-top">'
                f'      Top: <b>{top}</b>'
                f'    </div>'
                f'  </div>'
                f'</div>'
            )
        ui.html(f'<div class="dpr-z-grid">{cards}</div>')

        # ── Narrative ────────────────────────────────────────────────
        n = _build_narrative(zones, rpt)

        activity_html = "".join(
            f'<li>{b}</li>' for b in n["activity_bullets"]
        ) or '<li>No activities extracted.</li>'

        attention_html = "".join(
            f'<li>{b}</li>' for b in n["attention"]
        )

        recs_html = "".join(f"<li>{r}</li>" for r in n["recs"])

        ui.html(
            f'<div class="dpr-z-narr">'
            f'  <div class="dpr-z-narr-title">Site interpretation</div>'
            f'  <div class="dpr-z-narr-sub">'
            f'    Decision-support narrative derived from the aggregated '
            f'    report. Every claim below is backed by the rows on the '
            f'    Report Dashboard.'
            f'  </div>'

            f'  <div class="dpr-z-block">'
            f'    <div class="dpr-z-block-head">Site status</div>'
            f'    <div class="dpr-z-block-body"><p>{n["p1"]}</p></div>'
            f'  </div>'

            f'  <div class="dpr-z-block">'
            f'    <div class="dpr-z-block-head">Crew concentration</div>'
            f'    <div class="dpr-z-block-body"><p>{n["p2"]}</p></div>'
            f'  </div>'

            f'  <div class="dpr-z-block">'
            f'    <div class="dpr-z-block-head">Most active activities</div>'
            f'    <div class="dpr-z-block-body"><ul>{activity_html}</ul></div>'
            f'  </div>'

            f'  <div class="dpr-z-block">'
            f'    <div class="dpr-z-block-head">Attention required</div>'
            f'    <div class="dpr-z-block-body"><ul>{attention_html}</ul></div>'
            f'  </div>'

            f'  <div class="dpr-z-block">'
            f'    <div class="dpr-z-block-head">Recommendations</div>'
            f'    <div class="dpr-z-block-body"><ul>{recs_html}</ul></div>'
            f'  </div>'
            f'</div>'
        )

        # ── Footer ───────────────────────────────────────────────────
        with ui.row().classes("gap-2 mt-2 flex-wrap"):
            ui.button("Back to Dashboard",
                      on_click=lambda: ui.navigate.to("/results"))
            ui.button("Reconcile Sources",
                      on_click=lambda: ui.navigate.to("/reconcile"))
