import io
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from core.models import AggregatedReport
from core.exporters.styles import EXPORT_THEME


def _title_font(): return Font(bold=True, color=EXPORT_THEME["title"].lstrip("#"), size=14)
def _h2_font():    return Font(bold=True, color=EXPORT_THEME["title"].lstrip("#"), size=11)
def _body_font():  return Font(bold=False, color=EXPORT_THEME["body"].lstrip("#"), size=10)


def _fmt(item) -> str:
    if isinstance(item, dict):
        return " · ".join(f"{k}: {v}" for k, v in item.items() if v)
    return str(item)


def export_excel(report: AggregatedReport) -> bytes:
    wb = Workbook(); ws = wb.active; ws.title = "DPR"
    row = 1

    def put(value, font=None, col=1):
        nonlocal row
        c = ws.cell(row=row, column=col, value=value)
        c.font = font or _body_font()
        c.alignment = Alignment(vertical="top", wrap_text=True)

    put("Daily Progress Report", _title_font()); row += 1
    if report.project_name:
        put(report.project_name, _h2_font()); row += 1
    row += 1

    for k, v in [("Date", report.report_date), ("Location", report.site_location),
                 ("Prepared By", report.prepared_by), ("Weather", report.weather)]:
        put(k, _h2_font(), col=1); put(v or "-", _body_font(), col=2); row += 1
    row += 1

    def section(title, items):
        nonlocal row
        if not items: return
        put(title, _h2_font()); row += 1
        for it in items:
            put(f"• {_fmt(it)}"); row += 1
        row += 1

    section("Personnel on Site", report.personnel_on_site)
    section("Work Progress", report.work_progress)
    section("Equipment", report.equipment)
    section("Materials", report.materials)
    section("HSE Observations", report.hse_observations)
    if report.incidents:
        put("Incidents", _h2_font()); row += 1
        put(report.incidents); row += 2
    section("Quality Checks", report.quality_checks)
    section("Issues & Risks", report.issues_risks)
    section("Next Day Plan", report.next_day_plan)
    section("Source Files", report.source_files)

    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 90

    buf = io.BytesIO(); wb.save(buf)
    return buf.getvalue()
