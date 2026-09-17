"""PDF export — Summary + compact landscape tables + logo header."""
from __future__ import annotations
import base64
import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether,
)

from core.models import AggregatedReport
from core.exporters.styles import EXPORT_THEME
from core import summary as SUM


GREEN  = colors.HexColor("#C75A00")   # Caterpillar dark orange for PDF
BLACK  = colors.HexColor(EXPORT_THEME["body"])
GREY   = colors.HexColor("#888888")
LIGHT  = colors.HexColor("#EEEEEE")
AMBER  = colors.HexColor("#B76E00")
RED    = colors.HexColor("#B00020")
PAGE   = landscape(A4)

_HIDDEN_COLUMNS = {"sources", "provenance"}

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
    "summary_buildings": {
        "building": 4.0, "floors": 2.0, "activities": 2.5,
        "top_activity": 9.0, "crew": 2.5,
    },
    "summary_activities": {
        "activity": 9.0, "buildings": 2.5, "rows": 2.5, "crew": 3.0,
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
        "cell_strong": ParagraphStyle(
            "DprCellStrong", parent=base["BodyText"],
            textColor=BLACK, fontName="Helvetica-Bold",
            fontSize=7.5, leading=9,
        ),
        "meta_label": ParagraphStyle(
            "DprMetaLabel", parent=base["BodyText"],
            textColor=BLACK, fontName="Helvetica-Bold",
            fontSize=8.5, leading=11,
        ),
        "meta_value": ParagraphStyle(
            "DprMetaValue", parent=base["BodyText"],
            textColor=BLACK, fontName="Helvetica",
            fontSize=8.5, leading=11,
        ),
        "exec": ParagraphStyle(
            "DprExec", parent=base["BodyText"],
            textColor=BLACK, fontName="Helvetica",
            fontSize=9, leading=12, spaceBefore=2, spaceAfter=4,
        ),
    }


def _column_widths(table_kind: str, keys: list[str], avail_w: float) -> list[float]:
    hints = _WIDTHS.get(table_kind)
    if hints:
        widths = [hints.get(k) for k in keys]
        if all(w is not None for w in widths):
            total = sum(widths)
            if total > 0:
                scale = avail_w / (total * cm)
                return [w * cm * scale for w in widths]
    n = len(keys)
    return [avail_w / n] * n


def _build_table(items: list, styles, *, table_kind: str = "",
                 keys_order: list[str] | None = None) -> Table | None:
    if not items:
        return None

    if isinstance(items[0], dict):
        keys: list[str] = []
        if keys_order:
            keys = [k for k in keys_order if k in items[0]]
        else:
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

    else:
        rows = [[Paragraph("Item", styles["cell_head"])]]
        for it in items:
            rows.append([Paragraph(_e(it), styles["cell"])])
        keys = ["item"]

    avail_w = PAGE[0] - 4 * cm
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


def _make_page_handler(project_name: str, logo_reader: ImageReader | None):
    def _on_page(canvas, doc):
        canvas.saveState()
        w, h = PAGE
        canvas.setStrokeColor(GREEN)
        canvas.setLineWidth(0.5)
        canvas.line(2 * cm, h - 1.3 * cm, w - 2 * cm, h - 1.3 * cm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GREY)
        canvas.drawString(2 * cm, h - 1.05 * cm,
                          f"DPR — {project_name or 'Untitled'}")
        if logo_reader is not None:
            try:
                canvas.drawImage(
                    logo_reader,
                    w - 2 * cm - 1.6 * cm, h - 1.15 * cm,
                    width=1.6 * cm, height=0.85 * cm,
                    preserveAspectRatio=True, mask='auto',
                )
            except Exception:
                pass
        canvas.setStrokeColor(GREEN)
        canvas.line(2 * cm, 1.3 * cm, w - 2 * cm, 1.3 * cm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GREY)
        canvas.drawString(
            2 * cm, 0.85 * cm,
            f"Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        )
        canvas.drawRightString(w - 2 * cm, 0.85 * cm, f"Page {doc.page}")
        canvas.restoreState()
    return _on_page


def _decode_logo(report: AggregatedReport) -> ImageReader | None:
    pm = report.project_meta or {}
    b64 = pm.get("logo_b64")
    if not b64:
        return None
    try:
        raw = base64.b64decode(b64)
        return ImageReader(io.BytesIO(raw))
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Summary section for the PDF
# ═══════════════════════════════════════════════════════════════════════════
_STATUS_COLORS = {
    "on_track":  GREEN,
    "attention": AMBER,
    "at_risk":   RED,
}


def _summary_story(report, S) -> list:
    s = SUM.compute(report)
    story: list = []

    # ── Status banner ────────────────────────────────────────────────
    status_color = _STATUS_COLORS.get(s["status"], GREEN)
    banner = Table(
        [[Paragraph(
            f'<b>STATUS: {_e(s["status_label"])}</b><br/>'
            f'<font size="8">{_e(s["status_detail"])}</font>',
            ParagraphStyle(
                "status", parent=S["body"],
                textColor=colors.white, fontName="Helvetica-Bold",
                fontSize=10, leading=13,
            ),
        )]],
        colWidths=[PAGE[0] - 4 * cm],
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), status_color),
        ("LEFTPADDING",  (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
    ]))
    story.append(Paragraph("Executive Summary", S["h2"]))
    story.append(banner)
    story.append(Spacer(1, 6))

    # ── Executive text ───────────────────────────────────────────────
    if s["exec_summary"]:
        story.append(Paragraph(_e(s["exec_summary"]), S["exec"]))

    # ── Grand totals ─────────────────────────────────────────────────
    totals_rows = [
        [Paragraph("<b>Total Crew</b>", S["cell_strong"]),
         Paragraph(f"{s['total_crew']} "
                   f"({s['skilled']} skilled · {s['helpers']} helpers)",
                   S["cell"]),
         Paragraph("<b>Quality Grade</b>", S["cell_strong"]),
         Paragraph(f"{s['quality'].grade} — score {s['quality'].score}/100",
                   S["cell"])],
        [Paragraph("<b>Work Rows</b>", S["cell_strong"]),
         Paragraph(str(s["total_rows"]), S["cell"]),
         Paragraph("<b>Buildings</b>", S["cell_strong"]),
         Paragraph(str(s["total_buildings"]), S["cell"])],
        [Paragraph("<b>Activities</b>", S["cell_strong"]),
         Paragraph(str(s["total_activities"]), S["cell"]),
         Paragraph("<b>Avg Progress</b>", S["cell_strong"]),
         Paragraph(f"{s['avg_progress']:.0f}%", S["cell"])],
    ]
    totals_t = Table(
        totals_rows,
        colWidths=[3.0 * cm, 8.5 * cm, 3.0 * cm, 8.5 * cm],
    )
    totals_t.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("LINEBELOW",    (0, 0), (-1, -2), 0.15, LIGHT),
    ]))
    story.append(totals_t)
    story.append(Spacer(1, 6))

    # ── Per-building table ───────────────────────────────────────────
    if s["buildings"]:
        rows_data = [{
            "building": f'Building {b["building"]}',
            "floors": b["floors"],
            "activities": b["activities"],
            "top_activity": b["top_activity"],
            "crew": b["crew"],
        } for b in s["buildings"]]
        tbl = _build_table(
            rows_data, S, table_kind="summary_buildings",
            keys_order=["building", "floors", "activities",
                        "top_activity", "crew"],
        )
        if tbl:
            story.append(Paragraph("Crew Distribution by Building", S["h2"]))
            story.append(tbl)
            story.append(Spacer(1, 6))

    # ── Per-activity table ───────────────────────────────────────────
    if s["activities"]:
        total_crew = s["total_crew"] or 1
        rows_data = [{
            "activity": a["activity"],
            "buildings": a["buildings"],
            "rows": a["rows"],
            "crew": f'{a["crew"]}  ({a["crew"] / total_crew * 100:.0f}%)',
        } for a in s["activities"]]
        tbl = _build_table(
            rows_data, S, table_kind="summary_activities",
            keys_order=["activity", "buildings", "rows", "crew"],
        )
        if tbl:
            story.append(Paragraph("Activity Breakdown", S["h2"]))
            story.append(tbl)
            story.append(Spacer(1, 6))

    # ── Decision flags ───────────────────────────────────────────────
    if s["flags"]:
        story.append(Paragraph("Decision Flags", S["h2"]))
        for f in s["flags"]:
            story.append(Paragraph(f"• {_e(f)}", S["bullet"]))
        story.append(Spacer(1, 6))
    else:
        story.append(Paragraph("Decision Flags", S["h2"]))
        story.append(Paragraph(
            "• No flags raised. Data is clean and consistent across sources.",
            S["bullet"],
        ))

    return story


# ═══════════════════════════════════════════════════════════════════════════
# Public entry
# ═══════════════════════════════════════════════════════════════════════════
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
    pm = report.project_meta or {}

    # ── Title + meta ─────────────────────────────────────────────────
    story.append(Paragraph("Daily Progress Report", S["title"]))
    display_name = pm.get("project_name") or report.project_name or ""
    if display_name:
        story.append(Paragraph(_e(display_name), S["subtitle"]))

    def _lbl(text):
        return Paragraph(_e(text), S["meta_label"])
    def _val(text):
        return Paragraph(_e(text if text else "—"), S["meta_value"])

    meta_rows = [
        [_lbl("Date"), _val(report.report_date),
         _lbl("Prepared By"), _val(report.prepared_by)],
        [_lbl("Location"),
         _val(pm.get("location") or report.site_location),
         _lbl("Weather"), _val(pm.get("weather") or report.weather)],
    ]
    company = pm.get("company_name") or ""
    contractor = pm.get("contractor") or ""
    consultant = pm.get("consultant") or ""
    if company or contractor:
        meta_rows.append([
            _lbl("Company"), _val(company),
            _lbl("Contractor / Sub"), _val(contractor),
        ])
    if consultant:
        meta_rows.append([
            _lbl("Consultant"), _val(consultant),
            _lbl(""), _val(""),
        ])

    meta_t = Table(
        meta_rows,
        colWidths=[2.0 * cm, 10.0 * cm, 2.8 * cm, 10.9 * cm],
    )
    meta_t.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING",   (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 2),
    ]))
    story.append(meta_t)
    story.append(Spacer(1, 8))

    # ── Summary section ──────────────────────────────────────────────
    story.extend(_summary_story(report, S))
    story.append(Spacer(1, 8))

    # ── Section helpers ──────────────────────────────────────────────
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

    logo_reader = _decode_logo(report)
    on_page = _make_page_handler(
        pm.get("project_name") or report.project_name or "",
        logo_reader,
    )
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buf.getvalue()


def _fmt_dict(d: dict) -> str:
    return " · ".join(f"{k}: {v}" for k, v in d.items() if v not in (None, ""))
