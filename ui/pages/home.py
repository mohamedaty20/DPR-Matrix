from nicegui import ui
from ui import state
from ui.components import section_title, log_console


def render():
    ui.label("DPR-Matrix").classes("text-4xl font-bold dpr-title")
    ui.label(
        "Upload site reports (PDF, XLSX, PNG, JPG, TXT) — "
        "the aggregator merges them into one Daily Progress Report."
    ).classes("text-white mb-4")

    ui.separator()

    with ui.card().classes("w-full"):
        section_title("1 · Upload")
        ui.label(
            "Upload widget coming online in the next pass. "
            "The shell, theme, database, and routing are live."
        ).classes("text-white")

        ui.label(
            f"Session files: {len(state.docs())} · "
            f"Max per file: {__import__('config').settings.MAX_UPLOAD_MB} MB · "
            f"Max files: {__import__('config').settings.MAX_FILES}"
        ).classes("text-white")

    with ui.row().classes("gap-3 mt-4"):
        ui.button("New Session", on_click=_reset)
        ui.button("Go to Results", on_click=lambda: ui.navigate.to("/results"))

    section_title("Activity Log")
    log_console()


def _reset():
    state.reset()
    ui.notify("Session cleared", color="green")
    ui.navigate.to("/")
