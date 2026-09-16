from core.models import AggregatedReport


def _fmt(item) -> str:
    if isinstance(item, dict):
        return " · ".join(f"{k}: {v}" for k, v in item.items() if v)
    return str(item)


def export_txt(report: AggregatedReport) -> str:
    L = ["=" * 60, "DAILY PROGRESS REPORT", "=" * 60]
    if report.project_name: L.append(report.project_name)
    L.append("")
    for k, v in [("Date", report.report_date), ("Location", report.site_location),
                 ("Prepared By", report.prepared_by), ("Weather", report.weather)]:
        L.append(f"{k}: {v or '-'}")
    L.append("")

    def section(title, items):
        if not items: return
        L.extend(["-" * 60, title.upper(), "-" * 60])
        L.extend(f"  • {_fmt(it)}" for it in items)
        L.append("")

    section("Personnel on Site", report.personnel_on_site)
    section("Work Progress", report.work_progress)
    section("Equipment", report.equipment)
    section("Materials", report.materials)
    section("HSE Observations", report.hse_observations)
    if report.incidents:
        L.extend(["-" * 60, "INCIDENTS", "-" * 60, report.incidents, ""])
    section("Quality Checks", report.quality_checks)
    section("Issues & Risks", report.issues_risks)
    section("Next Day Plan", report.next_day_plan)
    section("Source Files", report.source_files)
    return "\n".join(L)
