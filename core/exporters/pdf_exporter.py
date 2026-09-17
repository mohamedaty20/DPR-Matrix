"""PDF export — compact landscape tables, page header/footer, page numbers.

Layout notes (why landscape):
  Work Progress has ~12 columns. In A4 portrait each column gets ~1.2 cm
  and every cell wraps to 6-8 lines, turning one row into one page. A4
  landscape gives 25.7 cm of usable width and every cell fits on one line.
"""
from __future__ import annotations
import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether,
)

from core.models import AggregatedReport
from core.exporters.styles import EXPORT_THEME


# ---------------------------------------------------------------------------
# Style tokens
# ---------------------------------------------------------------------------
GREEN = colors.HexColor(EXPORT_THEME["title"])
BLACK = colors.HexColor(EXPORT_THEME["body"])
GREY  = colors.HexColor("#888888")
LIGHT = colors.HexColor("#EEEEEE")
PAGE  = landscape(A4)              # 29.7 cm × 21 cm

# Columns we never print. Same rule as the on-screen tables in
# ui/components.py — `sources` is file bookkeeping, `provenance` is a
# nested dict.
_HIDDEN_COLUMNS = {"sources", "provenance"}

# Column width hints per table type (in cm, in the order the keys appear).
# Anything not listed falls back to a proportional split.
_WIDTHS: dict[str, dict[str, float]] = {
    "work_progress": {
        "building": 1.4, "floor": 0.9, "zone": 1.4,
        "activity": 3.4,
        "quantity": 1.5, "unit": 0.9,
        "skilled": 1.3, "helpers": 1.3, "crew_total": 1.5,
        "progress_pct": 1.5, "confidence": 1.5,
        "notes": 6.0,
    },
    "equipment": {
        "name": 4.5, "model": 3.0, "quantity": 1.8,
        "status": 2.5, "location": 3.0, "notes": 8.0,
    },
    "materials": {
        "name": 5.5, "grade": 2.0, "quantity": 1.8, "unit": 1.2,
        "location": 3.0, "notes": 8.0,
    },
    "personnel": {
        "trade": 4.0, "count": 1.8, "building": 2.5, "notes": 14.0,
    },
}


def _e(s) -> str:
    return escape(str(s) if s is not None else "")


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "DprTitle", parent=base["Heading1"],
            textColor=GREEN, fontName="Helvetica-Bold",
            fontSize=18, leading=22, spaceAfter=2, alignment=TA_LEFT,
        ),
        "subtitle": ParagraphStyle(
            "DprSubtitle", parent=base["Heading2"],
            textColor=BLACK, fontName="Helvetica", fontSize=10, leading=13,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "DprH2", parent=base["Heading2"],
            textColor=GREEN, fontName="Helvetica-Bold",
            fontSize=11, leading=14, spaceBefore=8, spaceAfter=3,
        ),
        "h3": ParagraphStyle(
            "DprH3", parent=base["Heading3"],
            textColor=GREEN, fontName="Helvetica-Bold",
            fontSize=9.5, leading=12, spaceBefore=6, spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "DprBody", parent=base["BodyText"],
            textColor=BLACK, fontName="Helvetica", fontSize=9, leading=11.5,
        ),
        "bullet": ParagraphStyle(
            "DprBullet", parent=base["BodyText"],
            textColor=BLACK, fontName="Helvetica", fontSize=9, leading=11.5,
            leftIndent=10, bulletIndent=2,
        ),
        # Table cells — tight
        "cell": ParagraphStyle(
            "DprCell", parent=base["BodyText"],
            textColor=BLACK, fontName="Helvetica",
            fontSize=7.5, leading=9,
        ),
        "cell_head": ParagraphStyle(
            "DprCellHead", parent=base["BodyText"],
            textColor=GREEN, fontName="Helvetica-Bold",
            fontSize=7.5, leading=9,
        ),
    }


# ---------------------------------------------------------------------------
# Column widths
# ---------------------------------------------------------------------------
def _column_widths(table_kind: str, keys: list[str], avail_w: float) -> list[float]:
    hints = _WIDTHS.get(table_kind)
    if hints:
        widths = [hints.get(k) for k in keys]
        if all(w is not None for w in widths):
            total = sum(widths)
            # Scale to fill available width
            if total > 0:
                scale = avail_w / (total * cm)
                return [w * cm * scale for w in widths]

    # Fallback: proportional split
    n = len(keys)
    return [avail_w / n] * n


# ---------------------------------------------------------------------------
# Table builder
# ---------------------------------------------------------------------------
def _build_table(items: list, styles, *, table_kind: str = "") -> Table | None:
    if not items:
        return None

    # ----- List of dicts → 2D grid with header -----
    if isinstance(items[0], dict):
        keys: list[str] = []
        for it in items:
            for k in it.keys():
                if k in _HIDDEN_COLUMNS:
                    continue
                if k not in keys:
                    keys.append(k)
        if not keys:
            return None

        header = [
            Paragraph(_e(k.replace("_", " ").title()), styles["cell_head"])
            for k in keys
        ]
        rows = [header]
        for it in items:
            row_cells = []
            for k in keys:
                v = it.get(k, "")
                if isinstance(v, list):
                    v = ", ".join(str(x) for x in v)
                row_cells.append(Paragraph(_e(v), styles["cell"]))
            rows.append(row_cells)

    # ----- List of scalars → single-column table -----
    else:
        rows = [[Paragraph("Item", styles["cell_head"])]]
        for it in items:
            rows.append([Paragraph(_e(it), styles["cell"])])
        keys = ["item"]

    avail_w = PAGE[0] - 4 * cm          # 25.7 cm on landscape A4
    col_w = _column_widths(table_kind, keys, avail_w)

    t = Table(rows, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), LIGHT),
        ("LINEBELOW",     (0, 0), (-1, 0), 0.6, GREEN),
        ("LINEBELOW",     (0, 1), (-1, -1), 0.15, GREY),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 3),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


# ---------------------------------------------------------------------------
# Page header / footer
# ---------------------------------------------------------------------------
def _on_page(canvas, doc, project_name: str):
    canvas.saveState()
    w, h = PAGE
    # Header rule
    canvas.setStrokeColor(GREEN)
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, h - 1.3 * cm, w - 2 * cm, h - 1.3 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawString(2 * cm, h - 1.05 * cm,
                      f"DPR — {project_name or 'Untitled'}")
    canvas.drawRightString(w - 2 * cm, h - 1.05 * cm,
                           datetime.utcnow().strftime("%Y-%m-%d"))
    # Footer rule
    canvas.setStrokeColor(GREEN)
    canvas.line(2 * cm, 1.3 * cm, w - 2 * cm, 1.3 * cm)
    canvas.drawString(
        2 * cm, 0.85 * cm,
        f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
    )
    canvas.drawRightString(w - 2 * cm, 0.85 * cm, f"Page {doc.page}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------
def export_pdf(report: AggregatedReport) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=PAGE,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title="Daily Progress Report",
        author=report.prepared_by or "DPR-Matrix",
    )
    S = _styles()
    story = []

    # ---- Title block ----
    story.append(Paragraph("Daily Progress Report", S["title"]))
    if report.project_name:
        story.append(Paragraph(_e(report.project_name), S["subtitle"]))

    # ---- Meta grid (compact, 2 columns × 2 rows) ----
    meta = [
        [
            Paragraph("<b>Date</b>", S["cell"]),
            Paragraph(_e(report.report_date or "—"), S["cell"]),
            Paragraph("<b>Prepared By</b>", S["cell"]),
            Paragraph(_e(report.prepared_by or "—"), S["cell"]),
        ],
        [
            Paragraph("<b>Location</b>", S["cell"]),
            Paragraph(_e(report.site_location or "—"), S["cell"]),
            Paragraph("<b>Weather</b>", S["cell"]),
            Paragraph(_e(report.weather or "—"), S["cell"]),
        ],
    ]
    meta_t = Table(meta, colWidths=[2.0 * cm, 10.0 * cm, 2.5 * cm, 11.2 * cm])
    meta_t.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING",   (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
    ]))
    story.append(meta_t)
    story.append(Spacer(1, 6))

    # ---- Sections ----
    def bullet_section(title: str, items: list) -> None:
        if not items:
            return
        block = [Paragraph(_e(title), S["h2"])]
        for it in items:
            text = _e(it) if not isinstance(it, dict) else _e(_fmt_dict(it))
            block.append(Paragraph(f"• {text}", S["bullet"]))
        story.append(KeepTogether(block))

    def table_section(title: str, items: list, *, kind: str = "") -> None:
        if not items:
            return
        tbl = _build_table(items, S, table_kind=kind)
        if tbl is None:
            bullet_section(title, items)
            return
        story.append(Paragraph(_e(title), S["h2"]))
        story.append(tbl)
        story.append(Spacer(1, 4))

    # Order that engineers expect: work first, admin last
    table_section("Work Progress", report.work_progress, kind="work_progress")
    table_section("Personnel",     report.personnel,     kind="personnel")
    table_section("Equipment",     report.equipment,     kind="equipment")
    table_section("Materials",     report.materials,     kind="materials")

    bullet_section("HSE Observations", report.hse_observations)

    if report.incidents:
        story.append(KeepTogether([
            Paragraph("Incidents", S["h2"]),
            Paragraph(_e(report.incidents), S["body"]),
        ]))

    bullet_section("Quality Checks", report.quality_checks)
    bullet_section("Issues & Risks", report.issues_risks)
    bullet_section("Next Day Plan", report.next_day_plan)

    # NOTE: source file list is intentionally omitted from the PDF — file
    # names are bookkeeping, not engineering content. Users said they do
    # not want to see upload names in any exported table.

    # ---- Build ----
    on_page = lambda c, d: _on_page(c, d, report.project_name)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


def _fmt_dict(d: dict) -> str:
    return " · ".join(f"{k}: {v}" for k, v in d.items() if v not in (None, ""))
