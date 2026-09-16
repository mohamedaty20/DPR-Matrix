from nicegui import ui, run
from ui import state
from ui.components import section_title, log_console
from utils.files import validate_upload
from core.extractors.router import route
from core.aggregator import aggregate
from core.db import save_report, cleanup_old_reports
from core.errors import DPRMatrixError


def render():
    ui.label("DPR-Matrix").classes("text-4xl font-bold dpr-title")
    ui.label(
        "Upload site reports (PDF · XLSX · PNG · JPG · TXT) — "
        "the aggregator merges them into one Daily Progress Report."
    ).classes("text-white mb-4")
    ui.separator()

    status_label = ui.label("").classes("text-white")
    progress = ui.linear_progress(value=0.0).classes("w-full")

    def refresh_status():
        status_label.text = (
            f"Session: {len(state.docs())} file(s) loaded · "
            f"Report ready: {'yes' if state.report() else 'no'}"
        )
    refresh_status()

    # ------------------------------------------------------------------ upload
    async def handle_upload(e):
        filename = e.name
        try:
            data = e.content.read()
            validate_upload(filename, data)
            state.log(f"[..] extracting {filename} ({len(data)} bytes)")

            doc = await run.io_bound(route, data, filename)
            doc.meta["bytes"] = len(data)  # remember size for DB logging

            state.add_doc(doc)
            state.log(f"[ok] {filename} → {len(doc.raw_text)} chars extracted")
            state.log(f"[state] docs in session: {len(state.docs())}")
            progress.value = min(1.0, len(state.docs()) / 5)
            refresh_status()
            ui.notify(f"Extracted {filename}", color="green")
        except DPRMatrixError as ex:
            state.log(f"[err] {filename}: {ex}")
            ui.notify(str(ex), color="red")
        except Exception as ex:
            state.log(f"[err] {filename}: {type(ex).__name__}: {ex}")
            ui.notify(f"Unexpected error: {ex}", color="red")

    with ui.card().classes("w-full"):
        section_title("1 · Upload")
        ui.upload(
            label="Drop site reports here (multiple allowed)",
            on_upload=handle_upload,
            multiple=True,
            auto_upload=True,
            max_file_size=15 * 1024 * 1024,
        ).props("accept=.pdf,.xlsx,.xls,.png,.jpg,.jpeg,.txt").classes("w-full")
        progress

    # ---------------------------------------------------------------- aggregate
    async def run_aggregate():
        if not state.docs():
            ui.notify("Upload at least one file first", color="orange")
            return
        try:
            state.log(f"[run] aggregating {len(state.docs())} doc(s)…")
            ui.notify("Aggregating with Gemini…", color="green")

            report = await run.io_bound(aggregate, state.docs())
            state.log(f"[ok] aggregation complete · project={report.project_name!r}")
            state.set_report(report)

            # --- persist to Turso ---
            try:
                uploads_meta = [
                    {
                        "filename": d.filename,
                        "mime": d.mime,
                        "bytes": d.meta.get("bytes", 0),
                        "extracted_chars": len(d.raw_text),
                    }
                    for d in state.docs()
                ]
                rid = await run.io_bound(save_report, report, uploads_meta)
                state.set_report_id(rid)
                state.log(f"[db] saved as report #{rid}")

                await run.io_bound(cleanup_old_reports, 90)
            except Exception as db_ex:
                state.log(f"[warn] DB save failed: {db_ex}")

            ui.navigate.to("/results")
        except Exception as ex:
            state.log(f"[err] aggregation failed: {type(ex).__name__}: {ex}")
            ui.notify(f"Aggregation failed: {ex}", color="red")

    with ui.card().classes("w-full"):
        section_title("2 · Aggregate")
        ui.button("Aggregate Reports", on_click=run_aggregate)

    with ui.row().classes("gap-3 mt-4"):
        ui.button("History", on_click=lambda: ui.navigate.to("/history"))
        ui.button("New Session", on_click=_reset)

    section_title("Activity Log")
    log_console()


def _reset():
    state.reset()
    ui.notify("Session cleared", color="green")
    ui.navigate.to("/")
