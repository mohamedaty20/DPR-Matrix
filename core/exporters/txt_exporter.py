"""Plain-text export — clean, print-friendly."""
from __future__ import annotations
from core.models import AggregatedReport

LINE = "=" * 78
THIN = "-" * 78


def _fmt(item) -> str:
    if isinstance(item, dict):
        parts = []
        for k, v in item.items():
            if v in (None, "", []):
                continue
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v)
            parts.append(f"{k}: {v}")
        return " · ".join(parts)
    return str(item)


def export_txt(report: AggregatedReport) -> str:
    L = [LINE, "DAILY PROGRESS REPORT", LINE]
    if report.project_name:
        L.append(report.project_name)
    L.append("")
    for k, v in [("Date", report.report_date), ("Location", report.site_location),
                 ("Prepared By", report.prepared_by), ("Weather", report.weather)]:
        L.append(f"{k:<14}: {v or '—'}")
    L.append("")

    def bullet(title, items):
        if not items:
            return
        L.extend([THIN, title.upper(), THIN])
        for it in items:
            L.append(f"  • {_fmt(it)}")
        L.append("")

    bullet("Personnel", report.personnel)
    bullet("Work Progress", report.work_progress)
    bullet("Equipment", report.equipment)
    bullet("Materials", report.materials)
    bullet("HSE Observations", report.hse_observations)
    if report.incidents:
        L.extend([THIN, "INCIDENTS", THIN, report.incidents, ""])
    bullet("Quality Checks", report.quality_checks)
    bullet("Issues & Risks", report.issues_risks)
    bullet("Next Day Plan", report.next_day_plan)
    if report.source_files:
        L.extend([THIN, "SOURCE FILES", THIN])
        L.extend(f"  • {f}" for f in report.source_files)
        L.append("")
    L.append(LINE)
    return "\n".join(L)
