"""Home — upload queue, live job status, aggregate, cancel."""
from __future__ import annotations

from nicegui import ui, run

from config import settings
from core.aggregator import aggregate
from core.db import save_report, cleanup_old_reports
from core.errors import DPRMatrixError
from core.extractors.router import route
from ui import state
from ui.shell import page_shell
from ui.components import section_title, log_console
from utils.files import validate_upload


_BADGE_LABEL = {
    "queued":     "Queued",
    "extracting": "Extracting",
    "done":       "Done",
    "error":      "Error",
}

_AGGREGATE_TIMEOUT_SEC = 600.0


def render() -> None:
    with page_shell(
        active="home",
        title="Upload & Aggregate",
        subtitle="Upload site reports (PDF · XLSX · XLS · PNG · JPG · TXT). "
                 "Each file is extracted independently, then merged "
                 "deterministically into a single Daily Progress Report.",
    ):
        _body()


def _body() -> None:
    session_label = ui.label("").classes("dpr-muted")

    def refresh_session_label() -> None:
        q = state.queue_files()
        done = sum(1 for f in q if f["status"] == "done")
        session_label.text = (
            f"{len(q)} / {settings.MAX_FILES} file(s) queued · {done} completed · "
            f"report: {'ready' if state.report() else 'none'}"
        )

    @ui.refreshable
    def file_queue_panel() -> None:
        q = state.queue_files()
        if not q:
            ui.label("No files queued yet — drop them above.").classes("dpr-muted")
            return
        with ui.column().classes("w-full gap-2"):
            for f in q:
                with ui.row().classes(
                    "dpr-queue-row items-center w-full gap-3 no-wrap"
                ):
                    ui.label(f["name"]).classes("dpr-queue-name")
                    ui.label(f"{f['size'] / 1024:.1f} KB").classes("dpr-queue-size")
                    label = _BADGE_LABEL.get(f["status"], f["status"])
                    ui.label(label).classes(f"dpr-badge dpr-badge-{f['status']}")
                    ui.button(
                        icon="close",
                        on_click=lambda t=f["token"]: _remove_file(t),
                    ).props("flat dense round size=sm").classes("dpr-icon-btn")

    def _remove_file(token: str) -> None:
        state.remove_queued(token)
        file_queue_panel.refresh()
        refresh_session_label()

    async def handle_upload(e) -> None:
        filename = e.name
        try:
            if len(state.queue_files()) >= settings.MAX_FILES:
                raise DPRMatrixError(
                    f"Queue is at the {settings.MAX_FILES}-file limit. "
                    f"Remove a file or click Aggregate to proceed."
                )
            data = e.content.read()
            validate_upload(filename, data)
            state.enqueue(filename, data, e.type or "")
            state.log(f"[queue] + {filename} ({len(data)} bytes)")
            ui.notify(f"Queued {filename}", color="green")
            file_queue_panel.refresh()
            refresh_session_label()
        except DPRMatrixError as ex:
            state.log(f"[err] {filename}: {ex}")
            ui.notify(str(ex), color="red")
        except Exception as ex:
            state.log(f"[err] {filename}: {type(ex).__name__}: {ex}")
            ui.notify(f"Unexpected error: {ex}", color="red")

    with ui.card().classes("dpr-card w-full"):
        section_title("1 · Upload")
        ui.upload(
            label="Drop site reports here (multiple allowed)",
            on_upload=handle_upload,
            multiple=True,
            auto_upload=True,
            max_file_size=settings.MAX_UPLOAD_MB * 1024 * 1024,
        ).props("accept=.pdf,.xlsx,.xls,.png,.jpg,.jpeg,.txt").classes("w-full")
        ui.label(
            f"Files are validated on drop and queued — nothing runs until you "
            f"click Aggregate. Up to {settings.MAX_FILES} files, "
            f"{settings.MAX_UPLOAD_MB} MB each."
        ).classes("dpr-muted").style("margin-top: 10px;")

    with ui.card().classes("dpr-card w-full"):
        section_title("2 · Queue")
        file_queue_panel()
        refresh_session_label()

    running = {"active": False}

    async def run_aggregate() -> None:
        if running["active"]:
            return
        q = state.queue_files()
        if not q:
            ui.notify("Queue is empty", color="orange")
            return

        running["active"] = True
        run_btn.disable()
        cancel_btn.enable()
        state.clear_cancel()
        state.reset()
        state.log(f"[run] starting job on {len(q)} file(s)")
        ui.notify("Running…", color="green")

        try:
            docs: list = []
            total = len(q)
            for i, f in enumerate(q, start=1):
                if state.is_cancelled():
                    state.log(f"[cancel] aborted at {i}/{total}")
                    ui.notify("Cancelled", color="orange")
                    return
                state.set_status(f["token"], "extracting")
                file_queue_panel.refresh()
                refresh_session_label()
                state.log(f"[text] {i}/{total} · {f['name']}")
                try:
                    data = state.get_bytes(f["token"])
                    if data is None:
                        raise DPRMatrixError(f"Bytes for '{f['name']}' missing")
                    doc = await run.io_bound(route, data, f["name"], f["mime"])
                    doc.meta["bytes"] = len(data)
                    docs.append(doc)
                    state.log(f"[text] ok · {f['name']} → {len(doc.raw_text)} chars")
                except Exception as ex:
                    state.set_status(f["token"], "error", str(ex))
                    state.log(f"[text] fail · {f['name']}: "
                              f"{type(ex).__name__}: {ex}")
                file_queue_panel.refresh()

            if state.is_cancelled():
                state.log("[cancel] aborted before merge")
                ui.notify("Cancelled", color="orange")
                return

            if not docs:
                state.log("[err] no documents extracted — nothing to aggregate")
                ui.notify("Nothing to aggregate", color="red")
                return

            state.set_docs(docs)
            state.log(f"[llm] running Gemini extraction on {len(docs)} doc(s)")

            def on_event(kind: str, **payload) -> None:
                state.push_event(kind, **payload)

            report = await run.io_bound(
                aggregate,
                docs,
                on_event=on_event,
                should_cancel=state.is_cancelled,
                max_seconds=_AGGREGATE_TIMEOUT_SEC,
            )

            if report is None:
                state.log("[cancel] aggregation cancelled")
                ui.notify("Cancelled", color="orange")
                return

            state.set_report(report)
            state.log(
                f"[ok] report ready · project={report.project_name!r} · "
                f"{len(report.work_progress)} work rows · "
                f"{len(report.conflicts)} conflict(s)"
            )

            try:
                uploads_meta = [
                    {
                        "filename": d.filename,
                        "mime": d.mime,
                        "bytes": d.meta.get("bytes", 0),
                        "extracted_chars": len(d.raw_text),
                    }
                    for d in docs
                ]
                rid = await run.io_bound(save_report, report, uploads_meta)
                state.set_report_id(rid)
                state.log(f"[db] saved as report #{rid}")
                await run.io_bound(cleanup_old_reports, 90)
            except Exception as db_ex:
                state.log(f"[warn] DB save failed: {db_ex}")

            for f in state.queue_files():
                if f["status"] != "error":
                    state.set_status(f["token"], "done")
            file_queue_panel.refresh()
            refresh_session_label()

            ui.navigate.to("/results")

        except Exception as ex:
            state.log(f"[err] job crashed: {type(ex).__name__}: {ex}")
            ui.notify(f"Job failed: {ex}", color="red")
        finally:
            running["active"] = False
            run_btn.enable()
            cancel_btn.disable()
            refresh_session_label()

    def _cancel() -> None:
        state.request_cancel()
        state.log("[cancel] requested — will stop after current file")
        ui.notify("Cancelling…", color="orange")

    with ui.card().classes("dpr-card w-full"):
        section_title("3 · Run")
        with ui.row().classes("gap-2 items-center"):
            run_btn = ui.button("Aggregate", on_click=run_aggregate) \
                .classes("dpr-btn-primary")
            cancel_btn = ui.button("Cancel", on_click=_cancel) \
                .classes("dpr-btn-danger")
            cancel_btn.disable()

    def _clear_queue() -> None:
        state.clear_queue()
        file_queue_panel.refresh()
        refresh_session_label()
        ui.notify("Queue cleared", color="green")

    def _new_session() -> None:
        state.reset()
        state.clear_queue()
        state.clear_cancel()
        ui.notify("Session cleared", color="green")
        ui.navigate.to("/")

    with ui.row().classes("gap-2 mt-2"):
        ui.button("History", on_click=lambda: ui.navigate.to("/history"))
        ui.button("Clear Queue", on_click=_clear_queue)
        ui.button("New Session", on_click=_new_session)

    section_title("Activity Log", "Streaming status from the current run.")
    log_console()

    def _drain_events() -> None:
        events = state.drain_events()
        if not events:
            return
        for kind, payload in events:
            if kind == "file_start":
                state.log(
                    f"[llm] {payload.get('index', '?')}/"
                    f"{payload.get('total', '?')} · {payload.get('filename', '')}"
                )
            elif kind == "file_ok":
                state.log(f"[llm] ok · {payload.get('filename', '')}")
            elif kind == "file_err":
                err = payload.get("error", "")
                name = payload.get("filename", "")
                state.log(f"[llm] fail · {name}: {err}")
                for f in state.queue_files():
                    if f["name"] == name:
                        state.set_status(f["token"], "error", err)
            elif kind == "merge_start":
                state.log("[merge] deterministic Python merge…")
            elif kind == "done":
                state.log("[merge] done")
            elif kind == "cancelled":
                reason = payload.get("reason", "cancel")
                phase = payload.get("phase", "?")
                state.log(f"[cancel] aggregate stopped ({reason} · {phase})")
        file_queue_panel.refresh()
        refresh_session_label()

    ui.timer(0.3, _drain_events)
