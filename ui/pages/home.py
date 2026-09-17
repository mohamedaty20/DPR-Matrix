"""Home — compact upload, queue, animated AI-processing state."""
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
/* ── Native uploader, restyled as a drop zone ──────────────────── */
.dpr-drop-wrap .q-uploader {
  background: linear-gradient(180deg, #0c0c0f 0%, #08080a 100%) !important;
  border: 1.5px dashed rgba(242,116,12,0.35) !important;
  border-radius: 12px !important;
  box-shadow: none !important;
  width: 100% !important;
  transition: border-color .15s ease, background-color .15s ease;
}
.dpr-drop-wrap .q-uploader:hover {
  border-color: rgba(242,116,12,0.65) !important;
  background: rgba(242,116,12,0.02) !important;
}
.dpr-drop-wrap .q-uploader__header {
  background: transparent !important;
  color: #e8e8ea !important;
  padding: 16px 18px !important;
  border: none !important;
  min-height: 0 !important;
  cursor: pointer !important;
}
.dpr-drop-wrap .q-uploader__title {
  color: #e8e8ea !important;
  font-size: 13px !important;
  font-weight: 600 !important;
}
.dpr-drop-wrap .q-uploader__subtitle {
  color: #85858c !important;
  font-size: 11px !important;
}
.dpr-drop-wrap .q-uploader__list { display: none !important; }
.dpr-drop-wrap .q-btn {
  background: transparent !important;
  color: #F2740C !important;
  border: 1px solid rgba(242,116,12,0.4) !important;
  border-radius: 8px !important;
  min-height: 30px !important;
  padding: 0 12px !important;
  font-size: 11.5px !important;
  font-weight: 600 !important;
}
.dpr-drop-wrap .q-btn:hover {
  background: rgba(242,116,12,0.08) !important;
}

/* ── Queue list ────────────────────────────────────────────────── */
.dpr-q-list { display: flex; flex-direction: column; gap: 4px; margin-top: 12px; }
.dpr-q-row {
  display: grid;
  grid-template-columns: 1fr auto auto auto;
  align-items: center;
  gap: 12px;
  padding: 7px 12px;
  background: #0c0c0f;
  border: 1px solid rgba(242,116,12,0.14);
  border-radius: 8px;
  font-size: 12px;
  min-height: 36px;
}
.dpr-q-name {
  color: #e8e8ea; font-weight: 500;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0;
}
.dpr-q-size { color: #4f4f56; font-size: 11px; white-space: nowrap; }
.dpr-q-status {
  font-size: 9.5px; font-weight: 700;
  letter-spacing: 0.08em; text-transform: uppercase;
  padding: 2px 8px; border-radius: 999px;
  border: 1px solid transparent; white-space: nowrap;
}
.dpr-q-queued     { color: #85858c; border-color: rgba(133,133,140,0.35); }
.dpr-q-extracting { color: #ffb020; border-color: rgba(255,176,32,0.4); }
.dpr-q-done       { color: #F2740C; border-color: rgba(242,116,12,0.4); }
.dpr-q-error      { color: #ff4d6a; border-color: rgba(255,77,106,0.4); }
.dpr-q-remove.q-btn {
  min-height: 22px !important; height: 22px !important;
  width: 22px !important; min-width: 22px !important;
  padding: 0 !important; border-radius: 6px !important;
  border-color: transparent !important; color: #4f4f56 !important;
  background: transparent !important;
}
.dpr-q-remove.q-btn:hover {
  color: #ff4d6a !important;
  background: rgba(255,77,106,0.08) !important;
  border-color: rgba(255,77,106,0.4) !important;
}
.dpr-q-empty {
  color: #4f4f56; font-size: 12px;
  text-align: center; padding: 14px 0; font-style: italic;
}

/* ── Action bar ────────────────────────────────────────────────── */
.dpr-action-bar {
  display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
  padding: 12px 16px;
  background: rgba(242,116,12,0.04);
  border: 1px solid rgba(242,116,12,0.20);
  border-radius: 12px; margin-top: 12px;
}
.dpr-action-bar-info {
  flex: 1; color: #85858c; font-size: 11.5px; min-width: 140px;
}
.dpr-action-bar-info b { color: #e8e8ea; font-weight: 600; }
.dpr-action-bar-info .err { color: #ff4d6a; font-weight: 700; }

/* ═══════════════════════════════════════════════════════════════
   AI processing state
   ═══════════════════════════════════════════════════════════════ */
.dpr-processing {
  background: linear-gradient(180deg, #0c0c0f 0%, #08080a 100%);
  border: 1px solid rgba(242,116,12,0.28);
  border-radius: 16px;
  padding: 44px 30px 34px 30px;
  text-align: center;
  width: 100%;
  animation: dpr-fade-in .4s ease;
}
@keyframes dpr-fade-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
.dpr-proc-title {
  color: #F2740C;
  font-family: 'JetBrains Mono', monospace;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 0.18em;
  margin: 0 0 8px 0;
  animation: dpr-proc-pulse 2s ease-in-out infinite;
}
@keyframes dpr-proc-pulse {
  0%, 100% { opacity: 1;   text-shadow: 0 0 0   rgba(242,116,12,0); }
  50%      { opacity: 0.75; text-shadow: 0 0 18px rgba(242,116,12,0.5); }
}
.dpr-proc-sub {
  color: #c8c8cc;
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.06em;
  margin-bottom: 6px;
}
.dpr-proc-dots::after {
  content: "";
  display: inline-block;
  width: 1.5em;
  text-align: left;
  animation: dpr-dots 1.4s steps(4, end) infinite;
}
@keyframes dpr-dots {
  0%   { content: ""; }
  25%  { content: "."; }
  50%  { content: ".."; }
  75%  { content: "..."; }
  100% { content: ""; }
}
.dpr-proc-hint {
  color: #4f4f56;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  margin-top: 24px;
}
.dpr-proc-graphic {
  max-width: 820px;
  margin: 24px auto 0 auto;
}
.dpr-proc-graphic svg {
  width: 100%;
  height: auto;
  display: block;
}
</style>
"""


_PROCESSING_HTML = """
<div class="dpr-processing">
  <div class="dpr-proc-title">PLEASE WAIT</div>
  <div class="dpr-proc-sub">
    AI is processing your files<span class="dpr-proc-dots"></span>
  </div>

  <div class="dpr-proc-graphic">
    <svg viewBox="0 0 820 300" preserveAspectRatio="xMidYMid meet"
         xmlns="http://www.w3.org/2000/svg">
      <defs>
        <pattern id="dprBlueprintGrid" width="24" height="24"
                 patternUnits="userSpaceOnUse">
          <path d="M 24 0 L 0 0 0 24" fill="none"
                stroke="rgba(242,116,12,0.08)" stroke-width="0.5"/>
        </pattern>
        <linearGradient id="dprScanGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%"   stop-color="rgba(242,116,12,0)"/>
          <stop offset="50%"  stop-color="rgba(242,116,12,0.55)"/>
          <stop offset="100%" stop-color="rgba(242,116,12,0)"/>
        </linearGradient>
        <linearGradient id="dprFillGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stop-color="rgba(242,116,12,0.10)"/>
          <stop offset="100%" stop-color="rgba(242,116,12,0.01)"/>
        </linearGradient>
      </defs>

      <!-- Blueprint grid -->
      <rect width="820" height="300" fill="url(#dprBlueprintGrid)"/>

      <!-- Ground line -->
      <line x1="0" y1="262" x2="820" y2="262"
            stroke="rgba(242,116,12,0.45)" stroke-width="1"/>

      <!-- Buildings — animated outline draw + subtle fill rise -->
      <g stroke="#F2740C" stroke-width="1.4" stroke-linejoin="round"
         fill="url(#dprFillGrad)">
        <!-- Building 1 -->
        <rect x="60" y="160" width="70" height="102"
              pathLength="100" stroke-dasharray="100" stroke-dashoffset="100">
          <animate attributeName="stroke-dashoffset"
                   values="100;0;0;100" keyTimes="0;0.35;0.75;1"
                   dur="6s" repeatCount="indefinite"/>
        </rect>
        <!-- Building 2 -->
        <rect x="180" y="105" width="90" height="157"
              pathLength="100" stroke-dasharray="100" stroke-dashoffset="100">
          <animate attributeName="stroke-dashoffset"
                   values="100;0;0;100" keyTimes="0;0.35;0.75;1"
                   dur="6s" begin="0.4s" repeatCount="indefinite"/>
        </rect>
        <!-- Building 3 -->
        <rect x="315" y="135" width="80" height="127"
              pathLength="100" stroke-dasharray="100" stroke-dashoffset="100">
          <animate attributeName="stroke-dashoffset"
                   values="100;0;0;100" keyTimes="0;0.35;0.75;1"
                   dur="6s" begin="0.8s" repeatCount="indefinite"/>
        </rect>
        <!-- Building 4 — tallest -->
        <rect x="440" y="70" width="105" height="192"
              pathLength="100" stroke-dasharray="100" stroke-dashoffset="100">
          <animate attributeName="stroke-dashoffset"
                   values="100;0;0;100" keyTimes="0;0.35;0.75;1"
                   dur="6s" begin="1.2s" repeatCount="indefinite"/>
        </rect>
        <!-- Building 5 -->
        <rect x="590" y="150" width="85" height="112"
              pathLength="100" stroke-dasharray="100" stroke-dashoffset="100">
          <animate attributeName="stroke-dashoffset"
                   values="100;0;0;100" keyTimes="0;0.35;0.75;1"
                   dur="6s" begin="1.6s" repeatCount="indefinite"/>
        </rect>
        <!-- Building 6 -->
        <rect x="700" y="185" width="65" height="77"
              pathLength="100" stroke-dasharray="100" stroke-dashoffset="100">
          <animate attributeName="stroke-dashoffset"
                   values="100;0;0;100" keyTimes="0;0.35;0.75;1"
                   dur="6s" begin="2.0s" repeatCount="indefinite"/>
        </rect>
      </g>

      <!-- Floor separator lines inside buildings -->
      <g stroke="rgba(242,116,12,0.25)" stroke-width="0.6">
        <line x1="60"  y1="193" x2="130" y2="193"/>
        <line x1="60"  y1="226" x2="130" y2="226"/>
        <line x1="180" y1="145" x2="270" y2="145"/>
        <line x1="180" y1="185" x2="270" y2="185"/>
        <line x1="180" y1="225" x2="270" y2="225"/>
        <line x1="315" y1="170" x2="395" y2="170"/>
        <line x1="315" y1="205" x2="395" y2="205"/>
        <line x1="440" y1="112" x2="545" y2="112"/>
        <line x1="440" y1="155" x2="545" y2="155"/>
        <line x1="440" y1="198" x2="545" y2="198"/>
        <line x1="590" y1="188" x2="675" y2="188"/>
        <line x1="590" y1="226" x2="675" y2="226"/>
      </g>

      <!-- Pulsing survey markers on top of each building -->
      <g fill="#F2740C">
        <circle cx="95"  cy="160" r="3">
          <animate attributeName="r"       values="3;6;3" dur="1.8s" repeatCount="indefinite"/>
          <animate attributeName="opacity" values="1;0.25;1" dur="1.8s" repeatCount="indefinite"/>
        </circle>
        <circle cx="225" cy="105" r="3">
          <animate attributeName="r"       values="3;6;3" dur="1.8s" begin="0.3s" repeatCount="indefinite"/>
          <animate attributeName="opacity" values="1;0.25;1" dur="1.8s" begin="0.3s" repeatCount="indefinite"/>
        </circle>
        <circle cx="355" cy="135" r="3">
          <animate attributeName="r"       values="3;6;3" dur="1.8s" begin="0.6s" repeatCount="indefinite"/>
          <animate attributeName="opacity" values="1;0.25;1" dur="1.8s" begin="0.6s" repeatCount="indefinite"/>
        </circle>
        <circle cx="492" cy="70" r="3">
          <animate attributeName="r"       values="3;6;3" dur="1.8s" begin="0.9s" repeatCount="indefinite"/>
          <animate attributeName="opacity" values="1;0.25;1" dur="1.8s" begin="0.9s" repeatCount="indefinite"/>
        </circle>
        <circle cx="632" cy="150" r="3">
          <animate attributeName="r"       values="3;6;3" dur="1.8s" begin="1.2s" repeatCount="indefinite"/>
          <animate attributeName="opacity" values="1;0.25;1" dur="1.8s" begin="1.2s" repeatCount="indefinite"/>
        </circle>
        <circle cx="732" cy="185" r="3">
          <animate attributeName="r"       values="3;6;3" dur="1.8s" begin="1.5s" repeatCount="indefinite"/>
          <animate attributeName="opacity" values="1;0.25;1" dur="1.8s" begin="1.5s" repeatCount="indefinite"/>
        </circle>
      </g>

      <!-- Scanning line sweeping left → right -->
      <rect x="-80" y="0" width="80" height="300" fill="url(#dprScanGrad)">
        <animate attributeName="x" from="-80" to="820"
                 dur="3.6s" repeatCount="indefinite"/>
      </rect>
    </svg>
  </div>

  <div class="dpr-proc-hint">
    Extracting · Merging · Verifying
  </div>
</div>
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
                    f"Queue is at the {settings.MAX_FILES}-file limit."
                )
            data = e.content.read()
            validate_upload(filename, data)

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
    # Main UI (hidden when processing)
    # ═══════════════════════════════════════════════════════════════
    main_ui = ui.element("div").classes("dpr-home-main")
    main_ui.style("display: flex; flex-direction: column; gap: 14px; width: 100%;")

    loading_ui = ui.element("div")
    loading_ui.style("display: none; width: 100%;")
    with loading_ui:
        ui.html(_PROCESSING_HTML)

    with main_ui:
        # ── Drop zone (native uploader) ─────────────────────────────
        with ui.element("div").classes("dpr-drop-wrap w-full"):
            ui.upload(
                label="Drop site reports here — or click to browse",
                on_upload=handle_upload,
                multiple=True,
                auto_upload=True,
                max_file_size=settings.MAX_UPLOAD_MB * 1024 * 1024,
            ).props(
                f'accept=.pdf,.xlsx,.xls,.png,.jpg,.jpeg,.txt '
                f'flat bordered no-thumbnails'
            ).classes("w-full")

        ui.html(
            f'<div style="color:#4f4f56;font-size:11px;'
            f'text-align:center;margin-top:-6px;">'
            f'Up to {settings.MAX_FILES} files · '
            f'{settings.MAX_UPLOAD_MB} MB each · '
            f'PDF · XLSX · XLS · PNG · JPG · TXT'
            f'</div>'
        )

        # ── Queue ───────────────────────────────────────────────────
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

        # ── Aggregate job ───────────────────────────────────────────
        running = {"active": False}
        btns = {"run": None, "cancel": None}

        def _show_processing() -> None:
            main_ui.style("display: none;")
            loading_ui.style("display: block;")

        def _hide_processing() -> None:
            main_ui.style("display: flex; flex-direction: column; gap: 14px; width: 100%;")
            loading_ui.style("display: none;")

        async def run_aggregate() -> None:
            if running["active"]:
                return
            q = state.queue_files()
            if not q:
                ui.notify("Queue is empty", color="orange", position="top")
                return

            running["active"] = True
            state.clear_cancel()
            state.reset()
            state.log(f"[run] starting job on {len(q)} file(s)")

            _show_processing()

            try:
                docs: list = []
                total = len(q)
                for i, f in enumerate(q, start=1):
                    if state.is_cancelled():
                        state.log(f"[cancel] aborted at {i}/{total}")
                        return
                    state.set_status(f["token"], "extracting")
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

                if state.is_cancelled():
                    state.log("[cancel] aborted before merge")
                    return
                if not docs:
                    state.log("[err] no documents extracted")
                    ui.notify("Nothing to aggregate", color="red", position="top")
                    return

                state.set_docs(docs)

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

                ui.navigate.to("/results")

            except Exception as ex:
                state.log(f"[err] job crashed: {type(ex).__name__}: {ex}")
                ui.notify(f"Job failed: {ex}", color="red", position="top")
            finally:
                running["active"] = False
                _hide_processing()
                _refresh_all()

        # ── Action bar ──────────────────────────────────────────────
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
                btns["cancel"] = ui.button(
                    "Cancel",
                    on_click=lambda: state.request_cancel(),
                ).classes("dpr-btn-danger")
                btns["cancel"].disable()

        queue_panel()
        action_bar()

    # ═══════════════════════════════════════════════════════════════
    # Event drain — silent; only updates queue badge states
    # ═══════════════════════════════════════════════════════════════
    def _drain_events() -> None:
        events = state.drain_events()
        if not events:
            return
        changed = False
        for kind, payload in events:
            if kind == "file_err":
                err = payload.get("error", "")
                name = payload.get("filename", "")
                for f in state.queue_files():
                    if f["name"] == name:
                        state.set_status(f["token"], "error", err)
                changed = True
        if changed and running["active"] is False:
            # Only refresh when we're not already in the processing view
            _refresh_all()

    ui.timer(0.5, _drain_events)
