"""Reusable widgets. Keep pages thin."""
from __future__ import annotations
from nicegui import ui
from ui import state


def section_title(text: str) -> None:
    ui.label(text).classes("text-2xl font-bold dpr-title mt-4")


def status_card(message: str, tone: str = "ok") -> None:
    colors = {"ok": "#00FF66", "warn": "#FFB300", "err": "#FF5555"}
    with ui.card().classes("w-full"):
        ui.label(message).style(f"color:{colors.get(tone, '#00FF66')};")


def log_console() -> ui.html:
    html = ui.html("").classes("dpr-console w-full")
    def refresh():
        html.content = "<br>".join(state.logs()[-80:]) or "— awaiting input —"
    ui.timer(1.0, refresh)
    refresh()
    return html


def report_preview() -> None:
    """Render the aggregated report with green titles / white body."""
    rpt = state.report()
    if rpt is None:
        ui.label("No report generated yet.").classes("text-white")
        return

    def kv(label: str, value):
        if value:
            ui.label(label).classes("dpr-title")
            ui.label(str(value)).classes("text-white")

    kv("Project", rpt.project_name)
    kv("Date", rpt.report_date)
    kv("Location", rpt.site_location)
    kv("Prepared By", rpt.prepared_by)
    kv("Weather", rpt.weather)

    for field_name in (
        "personnel_on_site", "work_progress", "equipment", "materials",
        "hse_observations", "quality_checks", "issues_risks", "next_day_plan",
    ):
        items = getattr(rpt, field_name, [])
        if items:
            ui.label(field_name.replace("_", " ").title()).classes("dpr-title")
            for item in items:
                ui.label(f"• {item}").classes("text-white")

    kv("Incidents", rpt.incidents)
    kv("Sources", ", ".join(rpt.source_files))
