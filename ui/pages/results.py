from nicegui import ui
from ui import state
from ui.components import section_title, report_preview


def render():
    ui.label("Aggregated Report").classes("text-4xl font-bold dpr-title")
    ui.separator()

    with ui.card().classes("w-full"):
        section_title("Preview")
        report_preview()

    with ui.row().classes("gap-3 mt-4"):
        ui.button("Back to Upload", on_click=lambda: ui.navigate.to("/"))
        ui.button("Refresh", on_click=lambda: ui.navigate.to("/results"))
