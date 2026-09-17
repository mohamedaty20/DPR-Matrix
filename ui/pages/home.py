"""Home — centered upload, custom drop zone, animated AI-processing state."""
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
/* ── Home container — everything centered ──────────────────────── */
.dpr-page-header { align-items: center !important; text-align: center !important; }
.dpr-page-title  { text-align: center !important; }
.dpr-page-subtitle {
  text-align: center !important;
  margin-left: auto !important;
  margin-right: auto !important;
}

.dpr-home-main {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 22px;
  width: 100%;
  max-width: 780px;
  margin: 0 auto;
  text-align: center;
}

/* ── Custom drop zone — no borders, centered text + plus ───────── */
.dpr-drop-wrap {
  width: 100%;
  display: flex;
  justify-content: center;
}

.dpr-drop-visual {
  width: 100%;
  max-width: 640px;
  padding: 56px 24px 48px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 28px;
  cursor: pointer;
  user-select: none;
  border: none !important;
  border-radius: 14px;
  transition: background-color .18s ease;
  -webkit-tap-highlight-color: transparent;
}
.dpr-drop-visual:hover {
  background: rgba(242, 116, 12, 0.035);
}
.dpr-drop-visual:active {
  background: rgba(242, 116, 12, 0.06);
}

.dpr-drop-text {
  color: #e8e8ea;
  font-family: 'JetBrains Mono', monospace;
  font-size: clamp(20px, 3.4vw, 30px);
  font-weight: 700;
  letter-spacing: 0.005em;
  line-height: 1.35;
  text-align: center;
  margin: 0;
}

.dpr-drop-plus {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #F2740C;
  font-family: 'JetBrains Mono', monospace;
  font-size: clamp(56px, 9vw, 84px);
  font-weight: 300;
  line-height: 0.85;
  transition: transform .18s ease, text-shadow .2s ease;
}
.dpr-drop-visual:hover .dpr-drop-plus {
  transform: scale(1.06);
  text-shadow: 0 0 26px rgba(242, 116, 12, 0.42);
}

/* The real Quasar uploader is present in the DOM but off-screen.
   We drive it via uploader.run_method('pickFiles'). */
.dpr-drop-input {
  position: fixed !important;
  top: -10000px !important;
  left: -10000px !important;
  width: 1px !important;
  height: 1px !important;
  opacity: 0 !important;
  pointer-events: none !important;
  overflow: hidden !important;
}

/* ── Hint line under the drop zone ─────────────────────────────── */
.dpr-home-hint {
  color: #4f4f56;
  font-size: 11.5px;
  letter-spacing: 0.02em;
  text-align: center;
  line-height: 1.6;
  margin-top: -6px;
}

/* ── Queue list ────────────────────────────────────────────────── */
.dpr-q-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 6px;
  width: 100%;
  max-width: 640px;
}
.dpr-q-row {
  display: grid;
  grid-template-columns: 1fr auto auto auto;
  align-items: center;
  gap: 12px;
  padding: 9px 14px;
  background: #0c0c0f;
  border: 1px solid rgba(242, 116, 12, 0.14);
  border-radius: 8px;
  font-size: 12px;
  min-height: 40px;
  text-align: left;
}
.dpr-q-name {
  color: #e8e8ea;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
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
  min-height: 24px !important; height: 24px !important;
  width: 24px !important; min-width: 24px !important;
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
  color: #4f4f56; font-size: 12px;
  text-align: center; padding: 14px 0; font-style: italic;
}

/* ── Action bar (centered) ─────────────────────────────────────── */
.dpr-action-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  justify-content: center;
  padding: 14px 18px;
  background: rgba(242, 116, 12, 0.04);
  border: 1px solid rgba(242, 116, 12, 0.20);
  border-radius: 12px;
  width: 100%;
  max-width: 640px;
}
.dpr-action-bar-info {
  flex: 1 1 100%;
  color: #85858c;
  font-size: 11.5px;
  text-align: center;
  margin-bottom: 4px;
}
.dpr-action-bar-info b { color: #e8e8ea; font-weight: 600; }
.dpr-action-bar-info .err { color: #ff4d6a; font-weight: 700; }

/* ── Footer disclaimer ────────────────────────────────────────── */
.dpr-home-footer {
  width: 100%;
  max-width: 640px;
  margin: 40px auto 0 auto;
  padding: 18px 8px 0 8px;
  text-align: center;
  color: #6a6a72;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11.5px;
  font-weight: 400;
  letter-spacing: 0.01em;
  line-height: 1.65;
  border-top: 1px solid rgba(242, 116, 12, 0.10);
}

/* ═══════════════════════════════════════════════════════════════
   AI processing state — big "Please wait" + blinking rectangle
   ═══════════════════════════════════════════════════════════════ */
.dpr-processing {
  background: linear-gradient(180deg, #0c0c0f 0%, #08080a 100%);
  border: 1px solid rgba(242, 116, 12, 0.28);
  border-radius: 16px;
  padding: 44px 30px 34px 30px;
  text-align: center;
  width: 100%;
  max-width: 900px;
  margin: 0 auto;
  animation: dpr-fade-in .4s ease;
}
@keyframes dpr-fade-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
.dpr-proc-sub {
  color: #c8c8cc;
  font-family: 'JetBrains Mono', monospace;
  font-size: clamp(12px, 1.7vw, 13.5px);
  font-weight: 500;
  letter-spacing: 0.06em;
  margin: 0 0 20px 0;
}
.dpr-proc-title-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 18px;
  margin: 0 0 4px 0;
  flex-wrap: wrap;
}
.dpr-proc-title {
  color: #F2740C;
  font-family: 'JetBrains Mono', monospace;
  font-size: clamp(26px, 4.6vw, 40px);
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  line-height: 1.1;
  animation: dpr-proc-pulse 2.4s ease-in-out infinite;
}
@keyframes dpr-proc-pulse {
  0%, 100% { opacity: 1;    text-shadow: 0 0 0  rgba(242, 116, 12, 0); }
  50%      { opacity: 0.82; text-shadow: 0 0 24px rgba(242, 116, 12, 0.5); }
}
.dpr-proc-blink {
  display: inline-block;
  width: 26px;
  height: 13px;
  border-radius: 2px;
  background: rgba(255, 255, 255, 0.85);
  animation: dpr-blink 2.6s ease-in-out infinite;
}
@keyframes dpr-blink {
  0%, 100% { opacity: 0.06; }
  50%      { opacity: 0.55; }
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
  margin-top: 26px;
}
.dpr-proc-graphic {
  max-width: 820px;
  margin: 28px auto 0 auto;
}
.dpr-proc-graphic svg {
  width: 100%;
  height: auto;
  display: block;
}

/* ── Small-phone refinements ──────────────────────────────────── */
@media (max-width: 640px) {
  .dpr-home-main    { gap: 16px; }
  .dpr-drop-visual  { padding: 40px 14px 34px 14px; gap: 20px; }
  .dpr-drop-plus    { font-size: 60px; }
  .dpr-processing   { padding: 32px 16px 24px 16px; }
  .dpr-proc-title-row { gap: 12px; }
  .dpr-proc-blink   { width: 20px; height: 10px; }
  .dpr-q-row        { padding: 8px 10px; gap: 8px; font-size: 11.5px; }
  .dpr-home-footer  { font-size: 11px; margin-top: 28px; }
}
</style>
"""


_PROCESSING_HTML = """
<div class="dpr-processing">
  <div class="dpr-proc-sub">
    AI is processing your files<span class="dpr-proc-dots"></span>
  </div>

  <div class="dpr-proc-title-row">
    <span class="dpr-proc-title">Please wait</span>
    <span class="dpr-proc-blink"></span>
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
        <rect x="60" y="160" width="70" height="102"
              pathLength="100" stroke-dasharray="100" stroke-dashoffset="100">
          <animate attributeName="stroke-dashoffset"
                   values="100;0;0;100" keyTimes="0;0.35;0.75;1"
                   dur="6s" repeatCount="indefinite"/>
        </rect>
        <rect x="180" y="105" width="90" height="157"
              pathLength="100" stroke-dasharray="100" stroke-dashoffset="100">
          <animate attributeName="stroke-dashoffset"
                   values="100;0;0;100" keyTimes="0;0.35;0.75;1"
                   dur="6s" begin="0.4s" repeatCount="indefinite"/>
        </rect>
        <rect x="315" y="135" width="80" height="127"
              pathLength="100" stroke-dasharray="100" stroke-dashoffset="100">
          <animate attributeName="stroke-dashoffset"
                   values="100;0;0;100" keyTimes="0;0.35;0.75;1"
                   dur="6s" begin="0.8s" repeatCount="indefinite"/>
        </rect>
        <rect x="440" y="70" width="105" height="192"
              pathLength="100" stroke-dasharray="100" stroke-dashoffset="100">
          <animate attributeName="stroke-dashoffset"
                   values="100;0;0;100" keyTimes="0;0.35;0.75;1"
                   dur="6s" begin="1.2s" repeatCount="indefinite"/>
        </rect>
        <rect x="590" y="150" width="85" height="112"
              pathLength="100" stroke-dasharray="100" stroke-dashoffset="100">
          <animate attributeName="stroke-dashoffset"
                   values="100;0;0;100" keyTimes="0;0.35;0.75;1"
                   dur="6s" begin="1.6s" repeatCount="indefinite"/>
        </rect>
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


_FOOTER_HTML = (
    '<div class="dpr-home-footer">'
    'This tool is using engineering trained AI module but results '
    'should be re-checked before decision making.'
    '</div>'
)


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
                ui.notify(
                    f"You've reached the {settings.MAX_FILES}-file limit "
                    f"for this project. Please remove a file from the "
                    f"queue before adding more.",
                    color="orange",
                    position="top",
                    group="upload-limit",
                    timeout=5000,
                )
                return

            data = e.content.read()
            validate_upload(filename, data)

            # Deduplicate accidental re-uploads
            for existing in state.queue_files():
                if (existing["name"] == filename
                        and existing["size"] == len(data)
                        and existing["status"] in ("queued", "extracting", "done")):
                    ui.notify(f"{filename} is already queued",
                              color="orange", position="top",
                              group="upload-dup")
                    return

            state.enqueue(filename, data, e.type or "")
            state.log(f"[queue] + {filename} ({len(data)} bytes)")
            ui.notify(f"Queued {filename}", color="green", position="top")
            _refresh_all()
        except DPRMatrixError as ex:
            state.log(f"[err] {filename}: {ex}")
            ui.notify(str(ex), color="red", position="top", group="upload-err")
        except Exception as ex:
            state.log(f"[err] {filename}: {type(ex).__name__}: {ex}")
            ui.notify(f"Upload failed: {ex}", color="red",
                      position="top", group="upload-err")

    # ═══════════════════════════════════════════════════════════════
    # Hidden uploader + custom centered drop-zone visual
    # ═══════════════════════════════════════════════════════════════
    uploader = ui.upload(
        on_upload=handle_upload,
        multiple=True,
        auto_upload=True,
        max_file_size=settings.MAX_UPLOAD_MB * 1024 * 1024,
    ).props(
        f'accept=.pdf,.xlsx,.xls,.png,.jpg,.jpeg,.txt '
        f'no-thumbnails'
    ).classes("dpr-drop-input")

    def _open_picker() -> None:
        try:
            uploader.run_method("pickFiles")
        except Exception as ex:
            state.log(f"[err] pickFiles failed: {type(ex).__name__}: {ex}")
            ui.notify("Could not open file picker — please tap again.",
                      color="red", position="top")

    # ═══════════════════════════════════════════════════════════════
    # Main UI (hidden when processing) + loading UI
    # ═══════════════════════════════════════════════════════════════
    main_ui = ui.element("div").classes("dpr-home-main")

    loading_ui = ui.element("div")
    loading_ui.style("display: none; width: 100%;")
    with loading_ui:
        ui.html(_PROCESSING_HTML)

    with main_ui:
        # ── Custom drop-zone visual ─────────────────────────────────
        with ui.element("div").classes("dpr-drop-wrap"):
            with ui.element("div").classes("dpr-drop-visual").on(
                "click", _open_picker
            ):
                ui.html(
                    '<div class="dpr-drop-text">Drop site reports here</div>'
                )
                ui.html('<div class="dpr-drop-plus">+</div>')

        # ── Hint line ───────────────────────────────────────────────
        ui.html(
            f'<div class="dpr-home-hint">'
            f'Up to {settings.MAX_FILES} files · '
            f'{settings.MAX_UPLOAD_MB} MB each · '
            f'PDF · XLSX · XLS · PNG · JPG · TXT'
            f'</div>'
        )

        # ── Queue panel ─────────────────────────────────────────────
        @ui.refreshable
        def queue_panel() -> None:
            q = state.queue_files()
            if not q:
                ui.html('<div class="dpr-q-empty">'
                        'Queue is empty — click the + above to add files.'
                        '</div>')
                return
            with ui.element("div").classes("dpr-q-list"):
                for f in q:
                    status = f.get("status", "queued")
                    with ui.element("div").classes("dpr-q-row"):
                        ui.html(
                            f'<span class="dpr-q-name">'
                            f'{escape(f["name"])}</span>'
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

        def _show_processing() -> None:
            main_ui.set_visibility(False)
            loading_ui.set_visibility(True)

        def _hide_processing() -> None:
            main_ui.set_visibility(True)
            loading_ui.set_visibility(False)

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
                            raise DPRMatrixError(
                                f"Bytes for '{f['name']}' missing"
                            )
                        doc = await run.io_bound(
                            route, data, f["name"], f["mime"]
                        )
                        doc.meta["bytes"] = len(data)
                        docs.append(doc)
                        state.log(
                            f"[text] ok · {f['name']} → "
                            f"{len(doc.raw_text)} chars"
                        )
                    except Exception as ex:
                        state.set_status(f["token"], "error", str(ex))
                        state.log(
                            f"[text] fail · {f['name']}: "
                            f"{type(ex).__name__}: {ex}"
                        )

                if state.is_cancelled():
                    state.log("[cancel] aborted before merge")
                    return
                if not docs:
                    state.log("[err] no documents extracted")
                    ui.notify("Nothing to aggregate",
                              color="red", position="top")
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
                    f"[ok] report ready · "
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
                    rid = await run.io_bound(
                        save_report, report, uploads_meta
                    )
                    state.set_report_id(rid)
                    state.log(f"[db] saved as report #{rid}")
                    await run.io_bound(cleanup_old_reports, 90)
                except Exception as db_ex:
                    state.log(f"[warn] DB save failed: {db_ex}")

                for f in state.queue_files():
                    if f["status"] != "error":
                        state.set_status(f["token"], "done")

                # Item 9 — take the user to the report tab automatically.
                ui.navigate.to("/results")

            except Exception as ex:
                state.log(f"[err] job crashed: {type(ex).__name__}: {ex}")
                ui.notify(f"Job failed: {ex}", color="red", position="top")
            finally:
                running["active"] = False
                _hide_processing()
                _refresh_all()

        # ── Action bar (centered) ───────────────────────────────────
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
                ui.button(
                    f"Aggregate {n} file{'s' if n != 1 else ''}"
                    if n else "Aggregate",
                    on_click=run_aggregate,
                ).classes("dpr-btn-primary")
                cancel_btn = ui.button(
                    "Cancel",
                    on_click=lambda: state.request_cancel(),
                ).classes("dpr-btn-danger")
                cancel_btn.disable()

        queue_panel()
        action_bar()

        # ── Footer disclaimer (item 7) ──────────────────────────────
        ui.html(_FOOTER_HTML)

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
            _refresh_all()

    ui.timer(0.5, _drain_events)
