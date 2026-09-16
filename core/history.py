"""History adapter — loads recent reports from Turso and extracts signals."""
from __future__ import annotations

from core.db import list_reports, get_report
from core.normalize import to_float


def load_recent(limit: int = 7) -> list[dict]:
    """Newest first. Skips any report that fails to deserialize."""
    rows = list_reports(limit=limit)
    out = []
    for r in rows:
        try:
            rpt = get_report(r["id"])
            if rpt is None:
                continue
            out.append({
                "id": r["id"],
                "created_at": r.get("created_at", ""),
                "report_date": r.get("report_date", ""),
                "report": rpt,
            })
        except Exception:
            continue
    return out


def extract_signals(entries: list[dict]) -> list[dict]:
    """Compact per-day summary for LLM input."""
    out = []
    for e in entries:
        rpt = e["report"]
        sk = hp = 0
        qty: dict[str, float] = {}
        for r in rpt.work_progress:
            sk += int(to_float(r.get("skilled")) or 0)
            hp += int(to_float(r.get("helpers")) or 0)
            act = (r.get("activity") or "").strip()
            q = to_float(r.get("quantity"))
            if act and q:
                qty[act] = qty.get(act, 0) + q

        out.append({
            "date": e.get("report_date") or e.get("created_at", "")[:10],
            "report_id": e["id"],
            "project": rpt.project_name or "",
            "location": rpt.site_location or "",
            "weather": rpt.weather or "",
            "shift": rpt.shift or "",
            "manpower": {"skilled": sk, "helpers": hp, "total": sk + hp},
            "distinct_activities": len({
                r.get("activity") for r in rpt.work_progress if r.get("activity")
            }),
            "distinct_buildings": len({
                r.get("building") for r in rpt.work_progress if r.get("building")
            }),
            "quantities": {k: round(v, 2) for k, v in qty.items()},
            "hse_observations": rpt.hse_observations[:5],
            "quality_checks": rpt.quality_checks[:5],
            "issues_risks": rpt.issues_risks[:5],
            "incidents": rpt.incidents or "",
            "next_day_plan": rpt.next_day_plan[:3],
            "conflicts": len(rpt.conflicts),
        })
    return out
