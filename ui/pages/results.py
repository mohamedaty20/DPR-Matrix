from nicegui import ui
from ui import state
from ui.components import section_title, report_preview


def render():
    ui.label("Aggregated Report").classes("text-4xl font-bold dpr-title")
    ui.separator()

    rpt = state.report()

    if rpt is None:
        with ui.card().classes("w-full"):
            ui.label("⚠  No report in this session.").classes("dpr-title text-xl")
            ui.label(
                "Either aggregation failed, or this tab reloaded and cleared state. "
                "Go back to Upload, add files, and click Aggregate Reports."
            ).classes("text-white")
        with ui.row().classes("gap-3 mt-4"):
            ui.button("Back to Upload", on_click=lambda: ui.navigate.to("/"))
        return

    with ui.card().classes("w-full"):
        section_title("Preview")
        report_preview()

    with ui.card().classes("w-full"):
        section_title("Export")
        with ui.row().classes("gap-3"):
            ui.button("Download PDF",   on_click=_download_pdf)
            ui.button("Download Excel", on_click=_download_excel)
            ui.button("Download TXT",   on_click=_download_txt)

    with ui.row().classes("gap-3 mt-4"):
        ui.button("New Session", on_click=_new_session)


def _download_pdf():
    from core.exporters.pdf_exporter import export_pdf
    ui.download(export_pdf(state.report()), "DPR_Report.pdf")


def _download_excel():
    from core.exporters.excel_exporter import export_excel
    ui.download(export_excel(state.report()), "DPR_Report.xlsx")


def _download_txt():
    from core.exporters.txt_exporter import export_txt
    ui.download(export_txt(state.report()).encode("utf-8"), "DPR_Report.txt")


def _new_session():
    state.reset()
    ui.navigate.to("/")
