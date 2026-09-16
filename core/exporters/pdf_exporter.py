"""PDF export — real tables, page header/footer, page numbers.
Screen theme: green bold titles on black.
Export theme: green bold titles, black body on white."""
from __future__ import annotations
import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether,
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


def _e(s) -> str:
    return escape(str(s) if s is not None else "")


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "DprTitle", parent=base["Heading1"],
            textColor=GREEN, fontName="Helvetica-Bold",
            fontSize=22, leading=26, spaceAfter=4, alignment=TA_LEFT,
        ),
        "subtitle": ParagraphStyle(
            "DprSubtitle", parent=base["Heading2"],
            textColor=BLACK, fontName="Helvetica", fontSize=11, leading=14,
            spaceAfter=14,
        ),
        "h2": ParagraphStyle(
            "DprH2", parent=base["Heading2"],
            textColor=GREEN, fontName="Helvetica-Bold",
            fontSize=13, leading=17, spaceBefore=14, spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "DprH3", parent=base["Heading3"],
            textColor=GREEN, fontName="Helvetica-Bold",
            fontSize=11, leading=14, spaceBefore=8, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "DprBody", parent=base["BodyText"],
            textColor=BLACK, fontName="Helvetica", fontSize=10, leading=14,
        ),
        "bullet": ParagraphStyle(
            "DprBullet", parent=base["BodyText"],
            textColor=BLACK, fontName="Helvetica", fontSize=10, leading=14,
            leftIndent=14, bulletIndent=4,
        ),
        "cell": ParagraphStyle(
            "DprCell", parent=base["BodyText"],
            textColor=BLACK, fontName="Helvetica", fontSize=9, leading=12,
        ),
        "cell_head": ParagraphStyle(
            "DprCellHead", parent=base["BodyText"],
            textColor=GREEN, fontName="Helvetica-Bold", fontSize=9, leading=12,
        ),
    }


# ---------------------------------------------------------------------------
# Table builder — works for lists of dicts OR lists of scalars
# ---------------------------------------------------------------------------
def _build_table(items: list, styles) -> Table | None:
    if not items:
        return None

    # List of dicts → 2D with header
    if isinstance(items[0], dict):
        keys = []
        for it in items:
            for k in it.keys():
                if k not in keys:
                    keys.append(k)
        if not keys:
            return None

        header = [Paragraph(_e(k.replace("_", " ").title()), styles["cell_head"])
                  for k in keys]
        rows = [header]
        for it in items:
            rows.append([Paragraph(_e(it.get(k, "")), styles["cell"]) for k in keys])

    # List of scalars → single-column table
    else:
        rows = [[Paragraph("Item", styles["cell_head"])]]
        for it in items:
            rows.append([Paragraph(_e(it), styles["cell"])])

    n_cols = len(rows[0])
    avail_w = A4[0] - 4 * cm
    col_w = [avail_w / n_cols] * n_cols

    t = Table(rows, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0), LIGHT),
        ("LINEBELOW",    (0, 0), (-1, 0), 0.8, GREEN),
        ("LINEBELOW",    (0, 1), (-1, -1), 0.25, GREY),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
    ]))
    return t


# ---------------------------------------------------------------------------
# Page header / footer
# ---------------------------------------------------------------------------
def _on_page(canvas, doc, project_name: str):
    canvas.saveState()
    w, h = A4
    # Header rule
    canvas.setStrokeColor(GREEN)
    canvas.setLineWidth(0.6)
    canvas.line(2 * cm, h - 1.5 * cm, w - 2 * cm, h - 1.5 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawString(2 * cm, h - 1.2 * cm, f"DPR — {project_name or 'Untitled'}")
    # Footer
    canvas.line(2 * cm, 1.5 * cm, w - 2 * cm, 1.5 * cm)
    canvas.drawString(
        2 * cm, 1.0 * cm,
        f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
    )
    canvas.drawRightString(w - 2 * cm, 1.0 * cm, f"Page {doc.page}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------
def export_pdf(report: AggregatedReport) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="Daily Progress Report",
        author=report.prepared_by or "DPR-Matrix",
    )
    S = _styles()
    story = []

    # ---- Title block ----
    story.append(Paragraph("Daily Progress Report", S["title"]))
    if report.project_name:
        story.append(Paragraph(_e(report.project_name), S["subtitle"]))
    story.append(Spacer(1, 4))

    # ---- Meta grid ----
    meta = [
        ["Date",        _e(report.report_date or "—")],
        ["Location",    _e(report.site_location or "—")],
        ["Prepared By", _e(report.prepared_by or "—")],
        ["Weather",     _e(report.weather or "—")],
    ]
    meta_t = Table(meta, colWidths=[3.5 * cm, A4[0] - 7.5 * cm])
    meta_t.setStyle(TableStyle([
        ("FONT",        (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONT",        (1, 0), (1, -1), "Helvetica"),
        ("TEXTCOLOR",   (0, 0), (-1, -1), BLACK),
        ("FONTSIZE",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",  (0, 0), (-1, -1), 2),
        ("LINEBELOW",   (0, 0), (-1, -2), 0.2, LIGHT),
    ]))
    story.append(meta_t)

    # ---- Structured sections ----
    def bullet_section(title: str, items: list):
        if not items:
            return
        block = [Paragraph(_e(title), S["h2"])]
        for it in items:
            text = _e(it) if not isinstance(it, dict) else _e(_fmt_dict(it))
            block.append(Paragraph(f"• {text}", S["bullet"]))
        story.append(KeepTogether(block))

    def table_section(title: str, items: list):
        if not items:
            return
        tbl = _build_table(items, S)
        if tbl is None:
            bullet_section(title, items)
            return
        story.append(KeepTogether([Paragraph(_e(title), S["h2"]), tbl]))

    bullet_section("Personnel on Site", report.personnel_on_site)
    table_section("Work Progress", report.work_progress)
    table_section("Equipment", report.equipment)
    table_section("Materials", report.materials)
    bullet_section("HSE Observations", report.hse_observations)

    if report.incidents:
        story.append(KeepTogether([
            Paragraph("Incidents", S["h2"]),
            Paragraph(_e(report.incidents), S["body"]),
        ]))

    bullet_section("Quality Checks", report.quality_checks)
    bullet_section("Issues & Risks", report.issues_risks)
    bullet_section("Next Day Plan", report.next_day_plan)

    # ---- Sources footer block ----
    if report.source_files:
        story.append(Spacer(1, 16))
        story.append(Paragraph("Source Files", S["h3"]))
        for f in report.source_files:
            story.append(Paragraph(f"• {_e(f)}", S["bullet"]))

    # ---- Build with header/footer ----
    on_page = lambda c, d: _on_page(c, d, report.project_name)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


def _fmt_dict(d: dict) -> str:
    return " · ".join(f"{k}: {v}" for k, v in d.items() if v not in (None, ""))
