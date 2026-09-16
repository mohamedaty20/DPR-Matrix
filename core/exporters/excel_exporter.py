"""Excel export — one sheet per section, auto-filter, freeze panes,
green bold headers, black data."""
from __future__ import annotations
import io
import re

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from core.models import AggregatedReport
from core.exporters.styles import EXPORT_THEME


GREEN_RGB = EXPORT_THEME["title"].lstrip("#")
BLACK_RGB = EXPORT_THEME["body"].lstrip("#")

_TITLE_FONT = Font(bold=True, color=GREEN_RGB, size=16)
_H2_FONT    = Font(bold=True, color=GREEN_RGB, size=12)
_HEAD_FONT  = Font(bold=True, color=GREEN_RGB, size=10)
_BODY_FONT  = Font(color=BLACK_RGB, size=10)

_HEAD_FILL = PatternFill("solid", fgColor="E8F5E9")
_THIN = Side(border_style="thin", color="CCCCCC")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)


def _fmt(d) -> str:
    if isinstance(d, dict):
        return " · ".join(f"{k}: {v}" for k, v in d.items() if v not in (None, ""))
    return str(d)


def _autosize(ws, max_width=60):
    for col_cells in ws.columns:
        letter = get_column_letter(col_cells[0].column)
        longest = 0
        for c in col_cells:
            if c.value is None:
                continue
            for line in str(c.value).split("\n"):
                longest = max(longest, len(line))
        ws.column_dimensions[letter].width = min(max(longest + 2, 12), max_width)


def _write_header_sheet(ws, report: AggregatedReport):
    r = 1
    ws.cell(r, 1, "Daily Progress Report").font = _TITLE_FONT; r += 1
    if report.project_name:
        ws.cell(r, 1, report.project_name).font = _H2_FONT; r += 1
    r += 1
    for k, v in [("Date", report.report_date), ("Location", report.site_location),
                 ("Prepared By", report.prepared_by), ("Weather", report.weather)]:
        ws.cell(r, 1, k).font = _HEAD_FONT
        ws.cell(r, 2, v or "—").font = _BODY_FONT
        r += 1
    r += 1
    ws.cell(r, 1, "Sources").font = _HEAD_FONT; r += 1
    for f in report.source_files or []:
        ws.cell(r, 1, f"• {f}").font = _BODY_FONT; r += 1
    _autosize(ws)


def _write_list_sheet(ws, title: str, items: list):
    r = 1
    ws.cell(r, 1, title).font = _H2_FONT; r += 2
    if not items:
        ws.cell(r, 1, "(none)").font = _BODY_FONT
        _autosize(ws); return

    if isinstance(items[0], dict):
        keys = []
        for it in items:
            for k in it.keys():
                if k not in keys:
                    keys.append(k)
        for ci, k in enumerate(keys, start=1):
            c = ws.cell(r, ci, k.replace("_", " ").title())
            c.font = _HEAD_FONT; c.fill = _HEAD_FILL; c.border = _BORDER
        r += 1
        for it in items:
            for ci, k in enumerate(keys, start=1):
                v = it.get(k, "") or ""
                if isinstance(v, list):
                    v = ", ".join(str(x) for x in v)
                c = ws.cell(r, ci, v)
                c.font = _BODY_FONT; c.border = _BORDER
                c.alignment = Alignment(wrap_text=True, vertical="top")
            r += 1
        last_col = get_column_letter(len(keys))
        ws.auto_filter.ref = f"A{r - len(items) - 1}:{last_col}{r - 1}"
        ws.freeze_panes = ws.cell(r - len(items), 1)
    else:
        ws.cell(r, 1, "Item").font = _HEAD_FONT
        ws.cell(r, 1).fill = _HEAD_FILL
        r += 1
        for it in items:
            ws.cell(r, 1, str(it)).font = _BODY_FONT
            r += 1
        ws.freeze_panes = "A3"
    _autosize(ws)


def _write_text_sheet(ws, title: str, text: str):
    ws.cell(1, 1, title).font = _H2_FONT
    ws.cell(3, 1, text or "(none)").font = _BODY_FONT
    ws.cell(3, 1).alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 100


def export_excel(report: AggregatedReport) -> bytes:
    wb = Workbook()

    # Sheet 1: Summary
    ws = wb.active
    ws.title = "Summary"
    _write_header_sheet(ws, report)

    # Sheet 2: Personnel
    _write_list_sheet(wb.create_sheet("Personnel"), "Personnel",
                      report.personnel)

    # Sheet 3: Work Progress
    _write_list_sheet(wb.create_sheet("Work Progress"), "Work Progress",
                      report.work_progress)

    # Sheet 4: Equipment
    _write_list_sheet(wb.create_sheet("Equipment"), "Equipment",
                      report.equipment)

    # Sheet 5: Materials
    _write_list_sheet(wb.create_sheet("Materials"), "Materials",
                      report.materials)

    # Sheet 6: HSE
    _write_list_sheet(wb.create_sheet("HSE"), "HSE Observations",
                      report.hse_observations)

    # Sheet 7: Incidents
    if report.incidents:
        _write_text_sheet(wb.create_sheet("Incidents"), "Incidents",
                          report.incidents)

    # Sheet 8: Quality
    _write_list_sheet(wb.create_sheet("Quality"), "Quality Checks",
                      report.quality_checks)

    # Sheet 9: Risks
    _write_list_sheet(wb.create_sheet("Risks"), "Issues & Risks",
                      report.issues_risks)

    # Sheet 10: Next Day
    _write_list_sheet(wb.create_sheet("Next Day"), "Next Day Plan",
                      report.next_day_plan)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
