from nicegui import ui
from ui import state
from ui.components import section_title, report_preview


def render():
    ui.label("Aggregated Report").classes("text-4xl font-bold dpr-title")
    ui.separator()

    with ui.card().classes("w-full"):
        section_title("Preview")
        report_preview()

    if state.report() is not None:
        with ui.card().classes("w-full"):
            section_title("3 · Export")
            with ui.row().classes("gap-3"):
                ui.button("Download PDF", on_click=_download_pdf)
                ui.button("Download Excel", on_click=_download_excel)
                ui.button("Download TXT", on_click=_download_txt)

    with ui.row().classes("gap-3 mt-4"):
        ui.button("Back to Upload", on_click=lambda: ui.navigate.to("/"))
        ui.button("Refresh", on_click=lambda: ui.navigate.to("/results"))


def _download_pdf():
    from core.exporters.pdf_exporter import export_pdf
    ui.download(export_pdf(state.report()), "DPR_Report.pdf")


def _download_excel():
    from core.exporters.excel_exporter import export_excel
    ui.download(export_excel(state.report()), "DPR_Report.xlsx")


def _download_txt():
    from core.exporters.txt_exporter import export_txt
    ui.download(export_txt(state.report()).encode("utf-8"), "DPR_Report.txt")
