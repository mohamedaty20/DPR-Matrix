import io
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from core.models import AggregatedReport
from core.exporters.styles import EXPORT_THEME


def _e(s) -> str:
    return escape(str(s) if s is not None else "")


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("DprTitle", parent=base["Heading1"],
            textColor=colors.HexColor(EXPORT_THEME["title"]),
            fontName="Helvetica-Bold", fontSize=20, leading=24, spaceAfter=8),
        "h2": ParagraphStyle("DprH2", parent=base["Heading2"],
            textColor=colors.HexColor(EXPORT_THEME["title"]),
            fontName="Helvetica-Bold", fontSize=13, leading=17,
            spaceBefore=10, spaceAfter=4),
        "body": ParagraphStyle("DprBody", parent=base["BodyText"],
            textColor=colors.HexColor(EXPORT_THEME["body"]),
            fontName="Helvetica", fontSize=10, leading=14),
        "bullet": ParagraphStyle("DprBullet", parent=base["BodyText"],
            textColor=colors.HexColor(EXPORT_THEME["body"]),
            fontName="Helvetica", fontSize=10, leading=14, leftIndent=12),
    }


def _fmt(item) -> str:
    if isinstance(item, dict):
        return " · ".join(f"{k}: {v}" for k, v in item.items() if v)
    return str(item)


def export_pdf(report: AggregatedReport) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    S = _styles()
    story = [Paragraph("Daily Progress Report", S["title"])]
    if report.project_name:
        story.append(Paragraph(_e(report.project_name), S["h2"]))
    story.append(Spacer(1, 8))

    meta = [
        ["Date", _e(report.report_date or "-")],
        ["Location", _e(report.site_location or "-")],
        ["Prepared By", _e(report.prepared_by or "-")],
        ["Weather", _e(report.weather or "-")],
    ]
    t = Table(meta, colWidths=[4*cm, 12*cm])
    t.setStyle(TableStyle([
        ("TEXTCOLOR", (0,0), (-1,-1), colors.HexColor(EXPORT_THEME["body"])),
        ("FONT", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONT", (1,0), (1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story += [t, Spacer(1, 12)]

    def section(title, items):
        if not items: return
        story.append(Paragraph(title, S["h2"]))
        for it in items:
            story.append(Paragraph(f"• {_e(_fmt(it))}", S["bullet"]))
        story.append(Spacer(1, 6))

    section("Personnel on Site", report.personnel_on_site)
    section("Work Progress", report.work_progress)
    section("Equipment", report.equipment)
    section("Materials", report.materials)
    section("HSE Observations", report.hse_observations)
    if report.incidents:
        story.append(Paragraph("Incidents", S["h2"]))
        story.append(Paragraph(_e(report.incidents), S["body"]))
        story.append(Spacer(1, 6))
    section("Quality Checks", report.quality_checks)
    section("Issues & Risks", report.issues_risks)
    section("Next Day Plan", report.next_day_plan)
    section("Source Files", report.source_files)

    doc.build(story)
    return buf.getvalue()
