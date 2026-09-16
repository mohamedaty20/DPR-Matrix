import re
from nicegui import ui
from ui import state
from ui.components import section_title, report_preview


def _safe(s: str, fallback: str = "report") -> str:
    s = (s or "").strip()
    s = re.sub(r"[^\w\-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or fallback


def _stem() -> str:
    rpt = state.report()
    if rpt is None:
        return "DPR_report"
    proj = _safe(rpt.project_name, "project")
    date = _safe(rpt.report_date, "") or "undated"
    return f"DPR_{proj}_{date}"


def render():
    ui.label("Aggregated Report").classes("dpr-app-title")
    ui.separator()

    rpt = state.report()
    n_queue = len(state.queue_files())

    ui.label(
        f"Queue: {n_queue} file(s) · report: "
        f"{'ready' if rpt else 'none'} · log lines: {len(state.logs())}"
    ).classes("dpr-muted")

    if rpt is None:
        with ui.card().classes("dpr-card w-full"):
            ui.label("No report in this session.").classes("dpr-title text-xl")
            if n_queue == 0:
                ui.label(
                    "No files were uploaded. Go back, add at least one "
                    "PDF / XLSX / PNG / JPG / TXT, then click Aggregate."
                ).classes("text-white")
            else:
                ui.label(
                    f"{n_queue} file(s) are queued but no report was produced. "
                    "The job may have been cancelled or failed — check the "
                    "Activity Log on the upload page."
                ).classes("text-white")
        if state.logs():
            section_title("Last activity")
            with ui.card().classes("dpr-card w-full"):
                ui.html("<br>".join(state.logs()[-15:])) \
                    .classes("dpr-console w-full")
        with ui.row().classes("gap-3 mt-4"):
            ui.button("Back to Upload", on_click=lambda: ui.navigate.to("/"))
            ui.button("History", on_click=lambda: ui.navigate.to("/history"))
        return

    with ui.card().classes("dpr-card w-full"):
        section_title("Preview")
        report_preview()

    with ui.card().classes("dpr-card w-full"):
        section_title("Export")
        ui.label(f"Filename will be: {_stem()}.pdf / .xlsx / .txt") \
            .classes("dpr-muted")
        with ui.row().classes("gap-3"):
            ui.button("Download PDF",   on_click=_download_pdf)
            ui.button("Download Excel", on_click=_download_excel)
            ui.button("Download TXT",   on_click=_download_txt)

    with ui.row().classes("gap-3 mt-4"):
        if state.report_id():
            ui.label(f"Saved as report #{state.report_id()}") \
                .classes("dpr-muted").style("align-self:center;")
        ui.button("History", on_click=lambda: ui.navigate.to("/history"))
        ui.button("New Session", on_click=_new_session)


def _download_pdf():
    try:
        from core.exporters.pdf_exporter import export_pdf
        data = export_pdf(state.report())
        ui.download(data, f"{_stem()}.pdf")
    except Exception as e:
        import traceback
        traceback.print_exc()
        state.log(f"[err] PDF export: {type(e).__name__}: {e}")
        ui.notify(f"PDF export failed: {e}", color="red")


def _download_excel():
    try:
        from core.exporters.excel_exporter import export_excel
        data = export_excel(state.report())
        ui.download(data, f"{_stem()}.xlsx")
    except Exception as e:
        import traceback
        traceback.print_exc()
        state.log(f"[err] Excel export: {type(e).__name__}: {e}")
        ui.notify(f"Excel export failed: {e}", color="red")


def _download_txt():
    try:
        from core.exporters.txt_exporter import export_txt
        data = export_txt(state.report()).encode("utf-8")
        ui.download(data, f"{_stem()}.txt")
    except Exception as e:
        import traceback
        traceback.print_exc()
        state.log(f"[err] TXT export: {type(e).__name__}: {e}")
        ui.notify(f"TXT export failed: {e}", color="red")


def _new_session():
    state.reset()
    state.clear_queue()
    state.clear_cancel()
    ui.navigate.to("/")
