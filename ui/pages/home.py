"""Home — compact drop zone, tight queue, prominent Run button."""
from __future__ import annotations

from html import escape

from nicegui import ui, run

from config import settings
from core.aggregator import aggregate
from core.db import save_report, cleanup_old_reports
from core.errors import DPRMatrixError
from core.extractors.router import route
from ui import state
from ui.shell import page_shell
from utils.files import validate_upload


_AGGREGATE_TIMEOUT_SEC = 600.0


_HOME_CSS = """
<style>
/* Style the uploader to look like a drop zone — do NOT hide its header. */
.dpr-drop-wrap .q-uploader {
  background: linear-gradient(180deg, #0c0c0f 0%, #08080a 100%) !important;
  border: 1.5px dashed rgba(34,197,94,0.35) !important;
  border-radius: 12px !important;
  box-shadow: none !important;
  width: 100% !important;
  transition: border-color .15s ease, background-color .15s ease;
}
.dpr-drop-wrap .q-uploader:hover {
  border-color: rgba(34,197,94,0.6) !important;
  background: rgba(34,197,94,0.02) !important;
}
.dpr-drop-wrap .q-uploader__header {
  background: transparent !important;
  color: #e8e8ea !important;
  padding: 16px 18px !important;
  border: none !important;
  min-height: 0 !important;
  display: flex !important;
  align-items: center !important;
  gap: 12px !important;
  cursor: pointer !important;
}
.dpr-drop-wrap .q-uploader__header-content {
  flex: 1 !important;
}
.dpr-drop-wrap .q-uploader__title {
  color: #e8e8ea !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  line-height: 1.3 !important;
}
.dpr-drop-wrap .q-uploader__subtitle {
  color: #85858c !important;
  font-size: 11px !important;
  margin-top: 2px !important;
  line-height: 1.4 !important;
}
.dpr-drop-wrap .q-uploader__list { display: none !important; }
.dpr-drop-wrap .q-btn {
  background: transparent !important;
  color: #22c55e !important;
  border: 1px solid rgba(34,197,94,0.4) !important;
  border-radius: 8px !important;
  min-height: 30px !important;
  padding: 0 12px !important;
  font-size: 11.5px !important;
  font-weight: 600 !important;
}
.dpr-drop-wrap .q-btn:hover {
  background: rgba(34,197,94,0.08) !important;
  border-color: rgba(34,197,94,0.7) !important;
}

.dpr-q-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 14px;
}
.dpr-q-row {
  display: grid;
  grid-template-columns: 1fr auto auto auto;
  align-items: center;
  gap: 12px;
  padding: 7px 12px;
  background: #0c0c0f;
  border: 1px solid rgba(34,197,94,0.14);
  border-radius: 8px;
  font-size: 12px;
  min-height: 36px;
}
.dpr-q-name {
  color: #e8e8ea;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}
.dpr-q-size {
  color: #4f4f56;
  font-size: 11px;
  white-space: nowrap;
}
.dpr-q-status {
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid transparent;
  white-space: nowrap;
}
.dpr-q-queued     { color: #85858c; border-color: rgba(133,133,140,0.35); }
.dpr-q-extracting { color: #ffb020; border-color: rgba(255,176,32,0.4); }
.dpr-q-done       { color: #22c55e; border-color: rgba(34,197,94,0.4); }
.dpr-q-error      { color: #ff4d6a; border-color: rgba(255,77,106,0.4); }

.dpr-q-remove.q-btn {
  min-height: 22px !important;
  height: 22px !important;
  width: 22px !important;
  min-width: 22px !important;
  padding: 0 !important;
  border-radius: 6px !important;
  border-color: transparent !important;
  color: #4f4f56 !important;
  background: transparent !important;
}
.dpr-q-remove.q-btn:hover {
  color: #ff4d6a !important;
  background: rgba(255,77,106,0.08) !important;
  border-color: rgba(255,77,106,0.4) !important;
}

.dpr-q-empty {
  color: #4f4f56;
  font-size: 12px;
  text-align: center;
  padding: 14px 0;
  font-style: italic;
}

.dpr-action-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  padding: 12px 16px;
  background: rgba(34,197,94,0.04);
  border: 1px solid rgba(34,197,94,0.20);
  border-radius: 12px;
  margin-top: 12px;
}
.dpr-action-bar-info {
  flex: 1;
  color: #85858c;
  font-size: 11.5px;
  min-width: 140px;
}
.dpr-action-bar-info b {
  color: #e8e8ea;
  font-weight: 600;
}
.dpr-action-bar-info .err { color: #ff4d6a; font-weight: 700; }
</style>
"""


def render() -> None:
    with page_shell(
        active="home",
        title="Upload & Aggregate",
        subtitle="Drop site reports. Nothing runs until you click Aggregate.",
    ):
        ui.add_head_html(_HOME_CSS, shared=False)
        _body()


def _body() -> None:
    # ═══════════════════════════════════════════════════════════════
    # Upload handler
    # ═══════════════════════════════════════════════════════════════
    async def handle_upload(e) -> None:
        filename = e.name
        try:
            if len(state.queue_files()) >= settings.MAX_FILES:
                raise DPRMatrixError(
                    f"Queue is at the {settings.MAX_FILES}-file limit. "
                    f"Remove a file or aggregate first."
                )
            data = e.content.read()
            validate_upload(filename, data)

            # Dedupe by (name, size) — protects against mobile-browser
            # retry storms when the websocket blips during upload.
            for existing in state.queue_files():
                if (existing["name"] == filename
                        and existing["size"] == len(data)
                        and existing["status"] in ("queued", "extracting", "done")):
                    ui.notify(f"{filename} already queued",
                              color="orange", position="top")
                    return

            state.enqueue(filename, data, e.type or "")
            state.log(f"[queue] + {filename} ({len(data)} bytes)")
            ui.notify(f"Queued {filename}", color="green", position="top")
            _refresh_all()
        except DPRMatrixError as ex:
            state.log(f"[err] {filename}: {ex}")
            ui.notify(str(ex), color="red", position="top")
        except Exception as ex:
            state.log(f"[err] {filename}: {type(ex).__name__}: {ex}")
            ui.notify(f"Upload failed: {ex}", color="red", position="top")

    # ═══════════════════════════════════════════════════════════════
    # Drop zone — native Quasar uploader, themed to look like a zone.
    # The uploader's own header is what handles clicks, so we style
    # it rather than replacing it.
    # ═══════════════════════════════════════════════════════════════
    with ui.element("div").classes("dpr-drop-wrap w-full"):
        ui.upload(
            label="Drop site reports here — or click to browse",
            on_upload=handle_upload,
            multiple=True,
            auto_upload=True,
            max_file_size=settings.MAX_UPLOAD_MB * 1024 * 1024,
        ).props(
            f'accept=.pdf,.xlsx,.xls,.png,.jpg,.jpeg,.txt '
            f'flat bordered '
            f'no-thumbnails'
        ).classes("w-full")

    ui.html(
        f'<div style="color:#4f4f56;font-size:11px;'
        f'margin-top:8px;text-align:center;">'
        f'Up to {settings.MAX_FILES} files · {settings.MAX_UPLOAD_MB} MB each · '
        f'PDF · XLSX · XLS · PNG · JPG · TXT'
        f'</div>'
    )

    # ═══════════════════════════════════════════════════════════════
    # Queue
    # ═══════════════════════════════════════════════════════════════
    @ui.refreshable
    def queue_panel() -> None:
        q = state.queue_files()
        if not q:
            ui.html('<div class="dpr-q-empty">'
                    'Queue is empty — drop files above.</div>')
            return

        with ui.element("div").classes("dpr-q-list"):
            for f in q:
                status = f.get("status", "queued")
                with ui.element("div").classes("dpr-q-row"):
                    ui.html(
                        f'<span class="dpr-q-name">{escape(f["name"])}</span>'
                    )
                    size_kb = f["size"] / 1024
                    size_txt = (
                        f'{size_kb:.1f} KB' if size_kb < 1024
                        else f'{size_kb / 1024:.1f} MB'
                    )
                    ui.html(f'<span class="dpr-q-size">{size_txt}</span>')
                    ui.html(
                        f'<span class="dpr-q-status dpr-q-{status}">'
                        f'{status}</span>'
                    )
                    ui.button(
                        icon="close",
                        on_click=lambda t=f["token"]: _remove_file(t),
                    ).props("flat dense round").classes("dpr-q-remove")

    def _remove_file(token: str) -> None:
        state.remove_queued(token)
        _refresh_all()

    def _refresh_all() -> None:
        queue_panel.refresh()
        action_bar.refresh()

    # ═══════════════════════════════════════════════════════════════
    # Aggregate job
    # ═══════════════════════════════════════════════════════════════
    running = {"active": False}
    btns = {"run": None, "cancel": None}

    async def run_aggregate() -> None:
        if running["active"]:
            return
        q = state.queue_files()
        if not q:
            ui.notify("Queue is empty", color="orange", position="top")
            return

        running["active"] = True
        if btns["run"]: btns["run"].disable()
        if btns["cancel"]: btns["cancel"].enable()
        state.clear_cancel()
        state.reset()
        state.log(f"[run] starting job on {len(q)} file(s)")
        ui.notify("Running…", color="green", position="top")
        _refresh_all()

        try:
            docs: list = []
            total = len(q)
            for i, f in enumerate(q, start=1):
                if state.is_cancelled():
                    state.log(f"[cancel] aborted at {i}/{total}")
                    ui.notify("Cancelled", color="orange", position="top")
                    return
                state.set_status(f["token"], "extracting")
                _refresh_all()
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
                _refresh_all()

            if state.is_cancelled():
                state.log("[cancel] aborted before merge")
                ui.notify("Cancelled", color="orange", position="top")
                return

            if not docs:
                state.log("[err] no documents extracted")
                ui.notify("Nothing to aggregate", color="red", position="top")
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
                ui.notify("Cancelled", color="orange", position="top")
                return

            state.set_report(report)
            state.log(
                f"[ok] report ready · {len(report.work_progress)} work rows · "
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
            _refresh_all()
            ui.navigate.to("/results")

        except Exception as ex:
            state.log(f"[err] job crashed: {type(ex).__name__}: {ex}")
            ui.notify(f"Job failed: {ex}", color="red", position="top")
        finally:
            running["active"] = False
            if btns["run"]: btns["run"].enable()
            if btns["cancel"]: btns["cancel"].disable()
            _refresh_all()

    def _cancel() -> None:
        state.request_cancel()
        state.log("[cancel] requested")
        ui.notify("Cancelling…", color="orange", position="top")

    def _clear_queue() -> None:
        state.clear_queue()
        _refresh_all()
        ui.notify("Queue cleared", color="green", position="top")

    # ═══════════════════════════════════════════════════════════════
    # Action bar
    # ═══════════════════════════════════════════════════════════════
    @ui.refreshable
    def action_bar() -> None:
        q = state.queue_files()
        n = len(q)
        done = sum(1 for f in q if f.get("status") == "done")
        errored = sum(1 for f in q if f.get("status") == "error")

        info_html = f'<b>{n}</b> file(s) queued'
        if done:
            info_html += f' · <b>{done}</b> done'
        if errored:
            info_html += f' · <span class="err">{errored} failed</span>'

        with ui.element("div").classes("dpr-action-bar"):
            ui.html(f'<div class="dpr-action-bar-info">{info_html}</div>')
            btns["run"] = ui.button(
                f"Aggregate {n} file{'s' if n != 1 else ''}"
                if n else "Aggregate",
                on_click=run_aggregate,
            ).classes("dpr-btn-primary")
            btns["cancel"] = ui.button("Cancel", on_click=_cancel).classes(
                "dpr-btn-danger"
            )
            btns["cancel"].disable()
            ui.button("Clear queue", on_click=_clear_queue)

    queue_panel()
    action_bar()

    # ═══════════════════════════════════════════════════════════════
    # Footer actions
    # ═══════════════════════════════════════════════════════════════
    def _new_session() -> None:
        state.reset()
        state.clear_queue()
        state.clear_cancel()
        ui.notify("Session cleared", color="green", position="top")
        ui.navigate.to("/")

    with ui.row().classes("gap-2 mt-4 flex-wrap"):
        ui.button("History", on_click=lambda: ui.navigate.to("/history"))
        ui.button("Zones board", on_click=lambda: ui.navigate.to("/zones"))
        ui.button("New Session", on_click=_new_session)

    # ═══════════════════════════════════════════════════════════════
    # Collapsible activity log
    # ═══════════════════════════════════════════════════════════════
    log_open = {"value": False}

    with ui.element("div").classes("w-full").style("margin-top: 14px;"):
        header = ui.element("button").style(
            "background: transparent; border: 1px solid rgba(34,197,94,0.20);"
            "color: #85858c; border-radius: 8px; padding: 7px 14px;"
            "cursor: pointer; font-size: 10.5px; letter-spacing: 0.08em;"
            "text-transform: uppercase; font-weight: 600;"
        )
        with header:
            toggle_label = ui.html("▶ Activity log")

        log_body = ui.element("div").style(
            "display: none; margin-top: 10px;"
        )
        with log_body:
            from ui.components import log_console
            log_console()

    def _toggle_log() -> None:
        log_open["value"] = not log_open["value"]
        log_body.style(
            "display: block; margin-top: 10px;"
            if log_open["value"]
            else "display: none; margin-top: 10px;"
        )
        toggle_label.content = (
            "▼ Activity log" if log_open["value"] else "▶ Activity log"
        )

    header.on("click", _toggle_log)

    # ═══════════════════════════════════════════════════════════════
    # Event drain
    # ═══════════════════════════════════════════════════════════════
    def _drain_events() -> None:
        events = state.drain_events()
        if not events:
            return
        changed = False
        for kind, payload in events:
            if kind == "file_start":
                state.log(f"[llm] {payload.get('index','?')}/"
                          f"{payload.get('total','?')} · "
                          f"{payload.get('filename','')}")
            elif kind == "file_ok":
                state.log(f"[llm] ok · {payload.get('filename','')}")
            elif kind == "file_err":
                err = payload.get("error","")
                name = payload.get("filename","")
                state.log(f"[llm] fail · {name}: {err}")
                for f in state.queue_files():
                    if f["name"] == name:
                        state.set_status(f["token"], "error", err)
                changed = True
            elif kind == "merge_start":
                state.log("[merge] deterministic Python merge…")
            elif kind == "done":
                state.log("[merge] done")
            elif kind == "cancelled":
                reason = payload.get("reason","cancel")
                phase = payload.get("phase","?")
                state.log(f"[cancel] stopped ({reason} · {phase})")
        if changed:
            _refresh_all()

    ui.timer(0.5, _drain_events)
