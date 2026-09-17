"""Results — report dashboard. Items 10-23 implemented here."""
from __future__ import annotations

import base64
import re
from html import escape

from nicegui import ui, run

from core import analytics as A
from core import quality as Q
from core import production as PROD
from core import history as HIST
from core import summary as SUM
from core.db import update_report_payload
from ui import state
from ui.shell import page_shell
from ui.components import (
    bar_list,
    crew_rectangles,
    histogram,
    line_chart,
    matrix_view,
    panel,
    report_preview,
    section_title,
    stat_grid,
    top_list,
)


# ═══════════════════════════════════════════════════════════════════════════
# Page CSS
# ═══════════════════════════════════════════════════════════════════════════
_REPORT_CSS = """
<style>
/* ── Item 17 — Report Dashboard title larger + centered ─────────── */
.dpr-page-header { align-items: center !important; text-align: center !important; }
.dpr-page-title {
  font-size: clamp(22px, 3.6vw, 30px) !important;
  text-align: center !important;
}
.dpr-page-subtitle {
  text-align: center !important;
  margin-left: auto !important;
  margin-right: auto !important;
}

/* ── Drawer toggle — item 19 (professional arrow) ──────────────── */
.dpr-drawer-toggle {
  position: fixed;
  top: 62px;
  left: 16px;
  z-index: 45;
  width: 34px;
  height: 34px;
  border-radius: 999px;
  background: #0c0c0f;
  border: 1px solid rgba(242,116,12,0.42);
  color: #F2740C;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  line-height: 1;
  padding: 0 0 2px 0;
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  box-shadow: 0 2px 14px rgba(0,0,0,0.55);
  transition: border-color .12s ease, background .12s ease;
}
.dpr-drawer-toggle:hover {
  border-color: rgba(242,116,12,0.85);
  background: rgba(242,116,12,0.06);
}
@media (min-width: 820px) {
  .dpr-drawer-toggle { left: 248px; }
}

/* ── Drawer shell ──────────────────────────────────────────────── */
.dpr-drawer {
  position: fixed;
  top: 0;
  left: 0;
  height: 100vh;
  width: 340px;
  max-width: 92vw;
  background: linear-gradient(180deg, #0c0c0f 0%, #06060a 100%);
  border-right: 1px solid rgba(242,116,12,0.28);
  box-shadow: 10px 0 40px rgba(0,0,0,0.7);
  transform: translateX(-105%);
  transition: transform .22s ease;
  z-index: 70;
  overflow-y: auto;
  padding: 16px 16px 28px 16px;
  -webkit-overflow-scrolling: touch;
}
.dpr-drawer.open { transform: translateX(0); }

.dpr-drawer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.55);
  backdrop-filter: blur(2px);
  opacity: 0;
  pointer-events: none;
  transition: opacity .2s ease;
  z-index: 60;
}
.dpr-drawer-backdrop.open {
  opacity: 1;
  pointer-events: auto;
}

.dpr-drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(242,116,12,0.18);
  gap: 8px;
}
.dpr-drawer-title {
  color: #F2740C;
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-weight: 700;
}
.dpr-drawer-close {
  background: transparent;
  color: #85858c;
  border: 1px solid rgba(242,116,12,0.28);
  border-radius: 8px;
  width: 30px;
  height: 30px;
  min-width: 30px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  line-height: 1;
  padding: 0;
}
.dpr-drawer-close:hover {
  color: #F2740C;
  border-color: rgba(242,116,12,0.7);
}

/* Inputs inside drawer + header */
.dpr-drawer .q-field__native,
.dpr-drawer .q-field__native input,
.dpr-drawer input, .dpr-drawer textarea,
.dpr-report-header .q-field__native,
.dpr-report-header .q-field__native input,
.dpr-report-header input, .dpr-report-header textarea,
input.q-field__native, textarea.q-field__native {
  color: #e8e8ea !important;
  -webkit-text-fill-color: #e8e8ea !important;
  caret-color: #F2740C !important;
  font-size: 12.5px !important;
}
.dpr-drawer input::placeholder,
.dpr-report-header input::placeholder {
  color: #4f4f56 !important;
  -webkit-text-fill-color: #4f4f56 !important;
}
.dpr-drawer .q-field__control,
.dpr-report-header .q-field__control {
  background: #121216 !important;
}
.dpr-drawer .q-uploader {
  background: #121216 !important;
  border-color: rgba(242,116,12,0.28) !important;
}

.dpr-proj-logo {
  width: 100%;
  max-height: 80px;
  object-fit: contain;
  display: block;
  margin: 12px 0 10px 0;
  border-radius: 6px;
  background: #050506;
  padding: 8px;
  border: 1px solid rgba(242,116,12,0.18);
}
.dpr-proj-field { margin-bottom: 10px; }
.dpr-proj-label {
  color: #85858c;
  font-size: 9.5px;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  font-weight: 600;
  display: block;
  margin-bottom: 4px;
}

/* ── Report header (item 16 — reduced) ─────────────────────────── */
.dpr-report-main {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
  width: 100%;
}
.dpr-report-header {
  background: linear-gradient(180deg, #0c0c0f 0%, #08080a 100%);
  border: 1px solid rgba(242,116,12,0.20);
  border-radius: 12px;
  padding: 14px 16px;
}
.dpr-report-header-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  align-items: end;
}
@media (max-width: 640px) {
  .dpr-report-header-grid { grid-template-columns: 1fr; }
}
.dpr-report-source-note {
  color: #85858c;
  font-size: 11px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(242,116,12,0.10);
}
.dpr-report-source-note b { color: #e8e8ea; font-weight: 600; }

/* ── Download block (item 15) ──────────────────────────────────── */
.dpr-download-heading {
  color: #c8c8cc;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  margin: 0 0 8px 0;
}
.dpr-download-btn.q-btn {
  background: transparent !important;
  border: 1px solid #4a4a52 !important;
  color: #c8c8cc !important;
  min-height: 30px !important;
  height: 30px !important;
  padding: 0 16px !important;
  font-size: 11.5px !important;
  font-weight: 600 !important;
  border-radius: 6px !important;
  box-shadow: none !important;
  letter-spacing: 0.04em;
}
.dpr-download-btn.q-btn:hover {
  border-color: #F2740C !important;
  color: #F2740C !important;
  background: rgba(242,116,12,0.04) !important;
}

/* ── Tab row with Zones button (item 18) ───────────────────────── */
.dpr-tabs-row {
  display: flex;
  align-items: stretch;
  gap: 8px;
  flex-wrap: wrap;
  width: 100%;
}
.dpr-tabs { flex: 1; min-width: 0; }
.dpr-tabs .q-tab {
  min-height: 36px !important;
  padding: 0 12px !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
  font-size: 11.5px !important;
  font-weight: 600 !important;
}
.dpr-tabs .q-tab__label { font-size: 11.5px !important; }
.dpr-tabs .q-tab__icon { font-size: 16px !important; }
.dpr-zones-tab.q-btn {
  min-height: 36px !important;
  height: 36px !important;
  padding: 0 14px !important;
  font-size: 11.5px !important;
  font-weight: 600 !important;
  border: 1px solid rgba(242,116,12,0.28) !important;
  color: #c8c8cc !important;
  background: transparent !important;
  border-radius: 8px !important;
}
.dpr-zones-tab.q-btn:hover {
  border-color: #F2740C !important;
  color: #F2740C !important;
}

/* ── Summary cards ─────────────────────────────────────────────── */
.dpr-sum-card {
  background: linear-gradient(180deg, #0c0c0f 0%, #08080a 100%);
  border: 1px solid rgba(242,116,12,0.20);
  border-radius: 12px;
  padding: 16px 18px;
  margin-bottom: 14px;
}
.dpr-sum-title {
  color: #F2740C;
  font-size: 12.5px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-weight: 700;
  margin-bottom: 12px;
}
.dpr-sum-card-title-lg {
  color: #F2740C;
  font-size: 15px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-weight: 700;
  margin-bottom: 14px;
}
.dpr-sum-table { width: 100%; border-collapse: collapse; }
.dpr-sum-table th {
  text-align: left;
  padding: 7px 10px;
  color: #85858c;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 600;
  border-bottom: 1px solid rgba(242,116,12,0.15);
}
.dpr-sum-table th.num { text-align: right; }
.dpr-sum-table td {
  padding: 7px 10px;
  color: #e8e8ea;
  font-size: 12px;
  border-bottom: 1px solid rgba(242,116,12,0.06);
}
.dpr-sum-table td.num { text-align: right; color: #c8c8cc; font-size: 11.5px; }
.dpr-sum-table td.crew { text-align: right; color: #F2740C; font-weight: 700; font-size: 12px; }
.dpr-sum-table td.pct { color: #4f4f56; font-size: 10px; margin-left: 6px; }
.dpr-bldg-link {
  color: #F2740C;
  cursor: pointer;
  text-decoration: none;
  font-weight: 600;
  border-bottom: 1px dashed rgba(242,116,12,0.4);
}
.dpr-bldg-link:hover { color: #ffb020; border-bottom-color: #ffb020; }

/* ── Interactive flag cards (items 10, 11) ─────────────────────── */
.dpr-flag-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  background: rgba(242,116,12,0.04);
  border: 1px solid rgba(242,116,12,0.22);
  border-left: 3px solid #F2740C;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color .12s ease, background .12s ease;
}
.dpr-flag-card:hover {
  background: rgba(242,116,12,0.08);
  border-color: rgba(242,116,12,0.5);
}
.dpr-flag-card.warn { border-left-color: #ffb020; }
.dpr-flag-card.warn:hover { border-color: rgba(255,176,32,0.5); }
.dpr-flag-card.danger { border-left-color: #ff4d6a; }
.dpr-flag-card.danger:hover { border-color: rgba(255,77,106,0.5); }
.dpr-flag-card.info {
  cursor: default;
  border-left-color: #4f4f56;
  background: rgba(255,255,255,0.015);
}
.dpr-flag-card.info:hover {
  background: rgba(255,255,255,0.015);
  border-color: rgba(242,116,12,0.22);
}
.dpr-flag-label {
  color: #e8e8ea;
  font-size: 12.5px;
  line-height: 1.45;
  flex: 1;
}
.dpr-flag-label b { color: #F2740C; font-weight: 700; }
.dpr-flag-action {
  color: #85858c;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
}
.dpr-flag-action:hover { color: #F2740C; }

/* ── Modal card look ───────────────────────────────────────────── */
.q-dialog .q-card, .q-dialog .dpr-card {
  background: linear-gradient(180deg, #0c0c0f 0%, #08080a 100%) !important;
  border: 1px solid rgba(242,116,12,0.35) !important;
}
.dpr-modal-row {
  padding: 10px 0;
  border-bottom: 1px solid rgba(242,116,12,0.10);
}
.dpr-modal-row:last-child { border-bottom: none; }
.dpr-modal-field {
  color: #e8e8ea;
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 6px;
}
.dpr-modal-values {
  color: #85858c;
  font-size: 11px;
  line-height: 1.6;
  font-family: 'JetBrains Mono', monospace;
  margin-bottom: 8px;
}
.dpr-modal-pick {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.dpr-modal-pick label {
  color: #c8c8cc;
  font-size: 11.5px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid rgba(242,116,12,0.18);
}
.dpr-modal-pick label:hover {
  border-color: rgba(242,116,12,0.5);
  color: #e8e8ea;
}
</style>
"""


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════
def _safe(s: str, fallback: str = "report") -> str:
    s = (s or "").strip()
    s = re.sub(r"[^\w\-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or fallback


def _stem() -> str:
    rpt = state.report()
    if rpt is None:
        return "DPR_report"
    pd = state.project_details()
    proj = _safe(pd.get("project_name") or rpt.project_name or "project")
    date = _safe(rpt.report_date or "", "") or "undated"
    return f"DPR_{proj}_{date}"


def _download_pdf():
    try:
        from core.exporters.pdf_exporter import export_pdf
        ui.download(export_pdf(state.report()), f"{_stem()}.pdf")
    except Exception as e:
        state.log(f"[err] PDF export: {e}")
        ui.notify(f"PDF export failed: {e}", color="red")


def _download_excel():
    try:
        from core.exporters.excel_exporter import export_excel
        ui.download(export_excel(state.report()), f"{_stem()}.xlsx")
    except Exception as e:
        state.log(f"[err] Excel export: {e}")
        ui.notify(f"Excel export failed: {e}", color="red")


def _download_txt():
    try:
        from core.exporters.txt_exporter import export_txt
        ui.download(export_txt(state.report()).encode("utf-8"), f"{_stem()}.txt")
    except Exception as e:
        state.log(f"[err] TXT export: {e}")
        ui.notify(f"TXT export failed: {e}", color="red")


def _download_row():
    """Item 15 — no filled background, thin grey outline per button,
    'Download' heading above."""
    with ui.element("div").style("padding: 4px 2px 2px 2px;"):
        ui.html('<div class="dpr-download-heading">Download</div>')
        with ui.row().classes("gap-2 items-center"):
            ui.button("PDF", on_click=_download_pdf).classes("dpr-download-btn")
            ui.button("Excel", on_click=_download_excel).classes("dpr-download-btn")
            ui.button("TXT", on_click=_download_txt).classes("dpr-download-btn")


# ═══════════════════════════════════════════════════════════════════════════
# Sync helpers
# ═══════════════════════════════════════════════════════════════════════════
_MIRROR_TO_REPORT = {
    "project_name": "project_name",
    "location":     "site_location",
    "weather":      "weather",
    "shift":        "shift",
}


def _sync_report_from_session() -> None:
    rpt = state.report()
    if rpt is None:
        return
    pd = state.project_details()
    if not isinstance(rpt.project_meta, dict):
        rpt.project_meta = {}
    for k, v in pd.items():
        if k.startswith("logo_"):
            continue
        if v:
            rpt.project_meta[k] = v
    for src, dst in _MIRROR_TO_REPORT.items():
        v = pd.get(src)
        if v:
            setattr(rpt, dst, v)


def _hydrate_session_from_report() -> None:
    rpt = state.report()
    if rpt is None:
        return
    pm = rpt.project_meta or {}
    for k, v in pm.items():
        if k.startswith("logo_"):
            continue
        if v and not state.project_details().get(k):
            state.set_project_detail(k, v)
    if pm.get("logo_b64") and not state.get_project_logo():
        try:
            raw = base64.b64decode(pm["logo_b64"])
            state.set_project_logo(raw, pm.get("logo_mime", "image/png"))
        except Exception:
            pass


def _on_field_changed(key: str, value: str) -> None:
    value = value or ""
    state.set_project_detail(key, value)
    rpt = state.report()
    if rpt is None:
        return
    if not isinstance(rpt.project_meta, dict):
        rpt.project_meta = {}
    rpt.project_meta[key] = value
    dst = _MIRROR_TO_REPORT.get(key)
    if dst:
        setattr(rpt, dst, value)


def _persist_and_reload(rpt, message: str = "Saved") -> None:
    """Update the stored payload and refresh the page (items 10, 11)."""
    rid = state.report_id()
    if rid is None:
        ui.notify("No saved report — aggregate first", color="orange",
                  position="top")
        return
    try:
        update_report_payload(rid, rpt)
        ui.notify(message, color="green", position="top")
        ui.navigate.to("/results")
    except Exception as ex:
        state.log(f"[err] persist: {type(ex).__name__}: {ex}")
        ui.notify(f"Save failed: {ex}", color="red", position="top")


# ═══════════════════════════════════════════════════════════════════════════
# Project details drawer body — item 19 ordering
# ═══════════════════════════════════════════════════════════════════════════
def _render_project_details_body() -> None:
    pd = state.project_details()

    def _field(key: str, label: str, placeholder: str = "") -> None:
        with ui.element("div").classes("dpr-proj-field"):
            ui.label(label).classes("dpr-proj-label")
            ui.input(
                value=pd.get(key, "") or "",
                placeholder=placeholder,
                on_change=lambda e, k=key: _on_field_changed(k, e.value or ""),
            ).props("dense outlined").classes("w-full")

    # Item 19 — Project Name FIRST, logo LAST.
    _field("project_name", "Project name", "e.g. WTG Foundation Package")
    _field("location",     "Location",     "e.g. Ras Ghareb, Zone B")
    _field("company_name", "Company name", "e.g. Orascom Construction")
    _field("contractor",   "Contractor / Sub", "e.g. Hassan Allam")
    _field("consultant",   "Consultant",   "e.g. Dar Al-Handasah")
    _field("shift",        "Shift",        "e.g. Day")

    # ── Logo at the bottom ─────────────────────────────────────────
    ui.html(
        '<div style="margin-top:14px;padding-top:12px;'
        'border-top:1px solid rgba(242,116,12,0.14);"></div>'
    )
    ui.label("Company logo").classes("dpr-proj-label")

    logo = state.get_project_logo()
    if logo:
        data, mime = logo
        b64 = base64.b64encode(data).decode("ascii")
        ui.html(
            f'<img class="dpr-proj-logo" '
            f'src="data:{mime};base64,{b64}" alt="logo"/>'
        )

    def _on_logo(e):
        try:
            data = e.content.read()
            mime = e.type or "image/png"
            state.set_project_logo(data, mime)
            rpt = state.report()
            if rpt is not None:
                if not isinstance(rpt.project_meta, dict):
                    rpt.project_meta = {}
                rpt.project_meta["logo_b64"] = base64.b64encode(data).decode("ascii")
                rpt.project_meta["logo_mime"] = mime
            ui.notify("Logo updated", color="green", position="top")
            ui.navigate.to("/results")
        except Exception as ex:
            ui.notify(f"Logo upload failed: {ex}", color="red", position="top")

    ui.upload(
        label="Company logo",
        on_upload=_on_logo,
        auto_upload=True,
        max_file_size=1 * 1024 * 1024,
    ).props('accept="image/*" flat bordered dense').classes("w-full").style(
        "font-size: 11px;"
    )

    if logo:
        def _remove_logo():
            state.clear_project_logo()
            rpt = state.report()
            if rpt is not None and isinstance(rpt.project_meta, dict):
                rpt.project_meta.pop("logo_b64", None)
                rpt.project_meta.pop("logo_mime", None)
            ui.navigate.to("/results")
        ui.button("Remove logo", on_click=_remove_logo).classes(
            "dpr-btn-danger dpr-btn-xs w-full"
        ).style("margin-top: 6px;")

    async def _save_details():
        _sync_report_from_session()
        rid = state.report_id()
        if rid is None:
            ui.notify("No saved report yet — aggregate first",
                      color="orange", position="top")
            return
        try:
            rpt = state.report()
            await run.io_bound(update_report_payload, rid, rpt)
            state.log(f"[db] project details saved for report #{rid}")
            ui.notify("Details saved", color="green", position="top")
        except Exception as ex:
            state.log(f"[err] save details: {type(ex).__name__}: {ex}")
            ui.notify(f"Save failed: {ex}", color="red", position="top")

    ui.button("Save details", on_click=_save_details).classes(
        "dpr-btn-primary dpr-btn-xs w-full"
    ).style("margin-top: 12px;")


# ═══════════════════════════════════════════════════════════════════════════
# Report header — item 16 reduced
# ═══════════════════════════════════════════════════════════════════════════
def _render_report_header(rpt) -> None:
    with ui.element("div").classes("dpr-report-header"):
        ui.html('<div style="color:#F2740C;font-size:10.5px;'
                'letter-spacing:0.14em;text-transform:uppercase;'
                'font-weight:700;margin-bottom:10px;">Report header</div>')
        with ui.element("div").classes("dpr-report-header-grid"):
            with ui.element("div"):
                ui.label("Date").classes("dpr-proj-label")
                def _on_date(e):
                    rpt.report_date = e.value or ""
                ui.input(
                    value=rpt.report_date or "",
                    placeholder="YYYY-MM-DD",
                    on_change=_on_date,
                ).props("dense outlined").classes("w-full")
            with ui.element("div"):
                ui.label("Prepared by").classes("dpr-proj-label")
                def _on_prep(e):
                    rpt.prepared_by = e.value or ""
                ui.input(
                    value=rpt.prepared_by or "",
                    placeholder="Your name",
                    on_change=_on_prep,
                ).props("dense outlined").classes("w-full")

        ui.html(
            f'<div class="dpr-report-source-note">'
            f'<b>{len(rpt.source_files)}</b> source file(s)'
            f'</div>'
        )


# ═══════════════════════════════════════════════════════════════════════════
# Item 10 — hard conflict resolution modal
# ═══════════════════════════════════════════════════════════════════════════
def _open_conflict_modal(rpt, conflicts: list[dict]) -> None:
    """Modal listing each hard conflict, letting the user choose:
       (a) trust the AI-recommended resolution, or (b) drop the conflict.
       On confirm, updates rpt.conflicts and persists to Turso.
    """
    # Track per-conflict pick. Default = keep the AI-resolved value.
    picks: dict[int, str] = {i: "keep" for i in range(len(conflicts))}

    with ui.dialog() as dlg, ui.card().classes("dpr-card").style(
        "min-width: min(560px, 94vw); max-width: 620px; max-height: 82vh; "
        "overflow-y: auto;"
    ):
        ui.html(
            f'<div class="dpr-sum-title" style="margin-bottom:8px;">'
            f'Resolve {len(conflicts)} field conflict(s)</div>'
        )
        ui.html(
            '<div style="color:#85858c;font-size:11.5px;line-height:1.55;'
            'margin-bottom:14px;">'
            'Each item below shows what every source said for the same '
            'field. Choose the AI-recommended value, or drop the conflict.'
            '</div>'
        )

        for i, c in enumerate(conflicts):
            field = escape(str(c.get("field", "?")))
            values = c.get("values", []) or []
            resolved = escape(str(c.get("resolution", "") or "—"))
            reason = escape(str(c.get("reason", "") or ""))

            with ui.element("div").classes("dpr-modal-row"):
                ui.html(f'<div class="dpr-modal-field">{field}</div>')
                vals_html = "".join(
                    f'<div>· {escape(str(v))}</div>' for v in values
                )
                ui.html(f'<div class="dpr-modal-values">{vals_html}</div>')
                ui.html(
                    f'<div style="color:#F2740C;font-size:11.5px;'
                    f'  font-weight:600;margin-bottom:8px;">'
                    f'AI recommends: {resolved}</div>'
                )
                if reason:
                    ui.html(
                        f'<div style="color:#4f4f56;font-size:10.5px;'
                        f'  font-style:italic;margin-bottom:8px;">'
                        f'{reason}</div>'
                    )

                def _set(idx=i, val="keep"):
                    picks[idx] = val

                with ui.element("div").classes("dpr-modal-pick"):
                    ui.html(
                        f'<label onclick="this.parentElement'
                        f'.querySelectorAll(\'label\').forEach'
                        f'(l=>l.style.borderColor=\'rgba(242,116,12,0.18)\');'
                        f'this.style.borderColor=\'#F2740C\';'
                        f'">'
                        f'  <input type="radio" name="cf-{i}" checked '
                        f'         value="keep" '
                        f'         onchange="'
                        f'var el=this.closest(\'.dpr-modal-row\');'
                        f'">'
                        f'  Accept AI choice'
                        f'</label>'
                        f'<label onclick="this.parentElement'
                        f'.querySelectorAll(\'label\').forEach'
                        f'(l=>l.style.borderColor=\'rgba(242,116,12,0.18)\');'
                        f'this.style.borderColor=\'#ff4d6a\';">'
                        f'  <input type="radio" name="cf-{i}" '
                        f'         value="drop">'
                        f'  Remove conflict'
                        f'</label>'
                    )
                    # Wire the radio values into `picks` via on_change
                    def _radio_handler(e, idx=i):
                        try:
                            picks[idx] = "drop" if e.value == "drop" else "keep"
                        except Exception:
                            picks[idx] = "keep"
                    # We attach a single hidden radio group per row using
                    # NiceGUI's ui.radio is heavier; JS above keeps the
                    # chosen visual state and we read it on confirm via
                    # a compact fallback: accept = default.
                    # Simpler: expose two small NiceGUI buttons per row.
                    ui.button(
                        "Accept",
                        on_click=lambda idx=i: (
                            picks.__setitem__(idx, "keep"),
                            ui.notify("Marked: accept AI choice",
                                      color="green", position="top",
                                      group=f"cf-{idx}"),
                        ),
                    ).classes("dpr-btn-xs")
                    ui.button(
                        "Remove",
                        on_click=lambda idx=i: (
                            picks.__setitem__(idx, "drop"),
                            ui.notify("Marked: remove conflict",
                                      color="orange", position="top",
                                      group=f"cf-{idx}"),
                        ),
                    ).classes("dpr-btn-danger dpr-btn-xs")

        def _confirm():
            new_conflicts = []
            # Rebuild the conflict list — hard conflicts whose idx was
            # marked "drop" are removed; otherwise they stay with the
            # AI-recommended resolution recorded.
            # We match by identity order from the original list.
            for c in rpt.conflicts:
                if c in conflicts:
                    idx = conflicts.index(c)
                    if picks.get(idx) == "drop":
                        continue
                    c["resolved_by_user"] = True
                new_conflicts.append(c)
            rpt.conflicts = new_conflicts
            _persist_and_reload(
                rpt,
                f"Conflict resolution saved ({len(conflicts)} handled)",
            )
            dlg.close()

        with ui.row().classes("gap-2 mt-3 justify-end w-full"):
            ui.button("Cancel", on_click=dlg.close).classes("dpr-btn-xs")
            ui.button("Confirm", on_click=_confirm).classes(
                "dpr-btn-primary dpr-btn-xs"
            )

    dlg.open()


# ═══════════════════════════════════════════════════════════════════════════
# Item 11 — "Some headers should be unified" modal
# ═══════════════════════════════════════════════════════════════════════════
def _open_unify_headers_modal(rpt) -> None:
    """Show every activity label currently in use, let the user merge
    synonyms by picking a canonical name and marking others for rename."""
    from collections import Counter
    activity_counts: Counter = Counter()
    for r in rpt.work_progress:
        a = (r.get("activity") or "").strip()
        if a:
            activity_counts[a] += 1

    if not activity_counts:
        ui.notify("No activity headers to unify", color="orange",
                  position="top")
        return

    all_acts = sorted(activity_counts.keys(), key=lambda x: -activity_counts[x])
    # Map original -> canonical (defaults to itself = no change)
    rename_map: dict[str, str] = {a: a for a in all_acts}

    with ui.dialog() as dlg, ui.card().classes("dpr-card").style(
        "min-width: min(600px, 94vw); max-width: 680px; max-height: 82vh; "
        "overflow-y: auto;"
    ):
        ui.html(
            '<div class="dpr-sum-title" style="margin-bottom:8px;">'
            'Unify activity headers</div>'
        )
        ui.html(
            '<div style="color:#85858c;font-size:11.5px;line-height:1.55;'
            'margin-bottom:14px;">'
            'These are the activity labels found across your uploaded '
            'sources. If two labels describe the same work, pick a single '
            'canonical name — the website and the stored report will be '
            'updated immediately on confirm.'
            '</div>'
        )

        selects: dict[str, ui.select] = {}
        for a in all_acts:
            with ui.element("div").classes("dpr-modal-row"):
                ui.html(
                    f'<div class="dpr-modal-field">'
                    f'{escape(a)} '
                    f'<span style="color:#4f4f56;font-size:10.5px;">'
                    f'({activity_counts[a]} row(s))</span>'
                    f'</div>'
                )
                selects[a] = ui.select(
                    options=all_acts,
                    value=a,
                    label="Canonical name",
                    on_change=lambda e, src=a: rename_map.__setitem__(
                        src, e.value or src
                    ),
                ).props("dense outlined").classes("w-full")

        def _confirm():
            changed = 0
            for r in rpt.work_progress:
                a = (r.get("activity") or "").strip()
                if a in rename_map and rename_map[a] != a:
                    r["activity"] = rename_map[a]
                    changed += 1
            if changed == 0:
                ui.notify("No changes to apply", color="orange",
                          position="top")
                dlg.close()
                return
            _persist_and_reload(rpt, f"Unified {changed} row(s)")

        with ui.row().classes("gap-2 mt-3 justify-end w-full"):
            ui.button("Cancel", on_click=dlg.close).classes("dpr-btn-xs")
            ui.button("Confirm", on_click=_confirm).classes(
                "dpr-btn-primary dpr-btn-xs"
            )

    dlg.open()


# ═══════════════════════════════════════════════════════════════════════════
# Item 12 — building detail modal
# ═══════════════════════════════════════════════════════════════════════════
def _open_building_detail_modal(rpt, building_row: dict) -> None:
    bldg = str(building_row.get("building", "—"))
    rows = [
        r for r in rpt.work_progress
        if (r.get("building") or "—").strip() == bldg
    ]

    with ui.dialog() as dlg, ui.card().classes("dpr-card").style(
        "min-width: min(720px, 96vw); max-width: 820px; max-height: 82vh; "
        "overflow-y: auto;"
    ):
        ui.html(
            f'<div class="dpr-sum-title" style="margin-bottom:6px;">'
            f'Building {escape(bldg)} — full extracted data</div>'
        )
        ui.html(
            f'<div style="color:#85858c;font-size:11px;margin-bottom:12px;">'
            f'{building_row.get("rows", 0)} row(s) · '
            f'{building_row.get("crew", 0)} crew · '
            f'{building_row.get("skilled", 0)} skilled · '
            f'{building_row.get("assistants", 0)} assistants · '
            f'{building_row.get("floors", 0)} floor(s)'
            f'</div>'
        )

        if not rows:
            ui.html('<div class="dpr-panel-empty">'
                    'No detailed rows for this building.</div>')
        else:
            head = "".join(
                f'<th style="color:#F2740C;font-size:10px;'
                f'padding:5px 8px;text-align:{align};'
                f'border-bottom:1px solid #F2740C;'
                f'background:#2a1206;text-transform:uppercase;'
                f'letter-spacing:0.05em;">{lbl}</th>'
                for lbl, align in [
                    ("Floor", "left"), ("Activity", "left"),
                    ("Skilled", "right"), ("Assistant", "right"),
                    ("Crew", "right"),
                    ("Quantity", "right"), ("Unit", "left"),
                    ("Progress", "right"), ("Notes", "left"),
                ]
            )
            body = ""
            for i, r in enumerate(rows):
                bg = "#0a0a0a" if i % 2 == 0 else "#0b0d0e"
                notes = escape(str(r.get("notes") or "—"))
                body += (
                    f'<tr style="background:{bg};">'
                    f'<td style="padding:5px 8px;color:#e8e8ea;font-size:11.5px;">'
                    f'  {escape(str(r.get("floor") or "—"))}</td>'
                    f'<td style="padding:5px 8px;color:#e8e8ea;font-size:11.5px;">'
                    f'  {escape(str(r.get("activity") or "—"))}</td>'
                    f'<td style="padding:5px 8px;color:#c8c8cc;font-size:11.5px;'
                    f'    text-align:right;">'
                    f'  {escape(str(r.get("skilled") or "—"))}</td>'
                    f'<td style="padding:5px 8px;color:#c8c8cc;font-size:11.5px;'
                    f'    text-align:right;">'
                    f'  {escape(str(r.get("helpers") or "—"))}</td>'
                    f'<td style="padding:5px 8px;color:#F2740C;font-size:11.5px;'
                    f'    text-align:right;font-weight:700;">'
                    f'  {escape(str(r.get("crew_total") or "—"))}</td>'
                    f'<td style="padding:5px 8px;color:#c8c8cc;font-size:11.5px;'
                    f'    text-align:right;">'
                    f'  {escape(str(r.get("quantity") or "—"))}</td>'
                    f'<td style="padding:5px 8px;color:#85858c;font-size:11px;">'
                    f'  {escape(str(r.get("unit") or "—"))}</td>'
                    f'<td style="padding:5px 8px;color:#c8c8cc;font-size:11.5px;'
                    f'    text-align:right;">'
                    f'  {escape(str(r.get("progress_pct") or "—"))}</td>'
                    f'<td style="padding:5px 8px;color:#85858c;font-size:11px;">'
                    f'  {notes}</td>'
                    f'</tr>'
                )
            ui.html(
                '<div style="overflow-x:auto;background:#0a0a0a;'
                'border:1px solid rgba(242,116,12,0.18);border-radius:8px;">'
                '<table style="border-collapse:collapse;background:#0a0a0a;'
                'width:100%;">'
                f'<thead><tr>{head}</tr></thead>'
                f'<tbody>{body}</tbody>'
                '</table></div>'
            )

        with ui.row().classes("gap-2 mt-3 justify-end w-full"):
            ui.button("Close", on_click=dlg.close).classes("dpr-btn-xs")

    dlg.open()


# ═══════════════════════════════════════════════════════════════════════════
# Summary tab — items 10, 11, 12, 13, 15, 16
# ═══════════════════════════════════════════════════════════════════════════
def _summary_tab(rpt):
    s = SUM.compute(rpt)

    colors = {
        "on_track": ("#F2740C", "rgba(242,116,12,0.08)", "rgba(242,116,12,0.35)"),
        "attention": ("#ffb020", "rgba(255,176,32,0.10)", "rgba(255,176,32,0.35)"),
        "at_risk": ("#ff4d6a", "rgba(255,77,106,0.10)", "rgba(255,77,106,0.35)"),
    }
    fg, bg, border = colors.get(s["status"], colors["on_track"])

    # ── Status banner ────────────────────────────────────────────────
    ui.html(
        f'<div style="background:{bg};border:1px solid {border};'
        f'border-left:4px solid {fg};border-radius:12px;'
        f'padding:16px 20px;margin-bottom:14px;">'
        f'  <div style="display:flex;align-items:center;gap:12px;'
        f'      flex-wrap:wrap;">'
        f'    <span style="background:{fg};color:#050506;padding:4px 12px;'
        f'        border-radius:999px;font-size:11px;font-weight:800;'
        f'        letter-spacing:0.1em;">{s["status_label"]}</span>'
        f'    <span style="color:#e8e8ea;font-size:13px;font-weight:600;">'
        f'      Project status</span>'
        f'  </div>'
        f'  <div style="color:#c8c8cc;font-size:12px;line-height:1.55;'
        f'      margin-top:10px;">{escape(s["status_detail"])}</div>'
        f'</div>'
    )

    # ── Item 13 — Executive Summary title larger ─────────────────────
    ui.html(
        f'<div class="dpr-sum-card">'
        f'  <div class="dpr-sum-card-title-lg">Executive summary</div>'
        f'  <div style="color:#e8e8ea;font-size:12.5px;line-height:1.6;">'
        f'    {escape(s["exec_summary"])}'
        f'  </div>'
        f'</div>'
    )

    # ── Grand totals — item 12b: Work Rows KPI removed ───────────────
    stat_grid([
        {"label": "Total Crew", "value": A.fmt_count(s["total_crew"]),
         "sub": f"{s['skilled']} skilled · {s['assistants']} assistants",
         "tone": "primary"},
        {"label": "Avg Progress", "value": f"{s['avg_progress']:.0f}%",
         "sub": "across reported rows"},
        {"label": "Quality Grade", "value": s["quality"].grade,
         "sub": f"score {s['quality'].score}/100",
         "tone": s["grade_tone"]},
    ])

    # ── Crew distribution by building — item 12 ──────────────────────
    if s["buildings"]:
        rows = ""
        for b in s["buildings"]:
            bldg_label = escape(str(b["building"]))
            rows += (
                f'<tr>'
                f'<td><span class="dpr-bldg-link" data-bldg="{bldg_label}">'
                f'Building {bldg_label}</span></td>'
                f'<td class="num">{b["floors"]}</td>'
                f'<td class="num">{b["activities"]}</td>'
                f'<td class="crew">{b["crew"]}</td>'
                f'</tr>'
            )
        ui.html(
            f'<div class="dpr-sum-card">'
            f'  <div class="dpr-sum-title">Crew distribution by building</div>'
            f'  <div style="overflow-x:auto;">'
            f'  <table class="dpr-sum-table" id="dpr-crew-dist">'
            f'    <thead><tr>'
            f'      <th>Building</th>'
            f'      <th class="num">Floor - No</th>'
            f'      <th class="num">No. of Activities</th>'
            f'      <th class="num">Crew</th>'
            f'    </tr></thead>'
            f'    <tbody>{rows}</tbody>'
            f'  </table></div>'
            f'</div>'
        )

        # Attach click handler — read data-bldg from the clicked span
        def _handle_bldg_click(e):
            try:
                bldg = None
                if isinstance(e.args, dict):
                    # NiceGUI's generic event args may carry the target
                    bldg = e.args.get("bldg") or None
                if bldg is None:
                    return
                row = next(
                    (b for b in s["buildings"]
                     if str(b["building"]) == str(bldg)),
                    None,
                )
                if row:
                    _open_building_detail_modal(rpt, row)
            except Exception as ex:
                state.log(f"[err] bldg click: {ex}")

        # Simpler, robust approach — use per-building small buttons via JS
        # We attach a click listener to the table that reads data-bldg.
        ui.run_javascript(
            """
            (function() {
              var tbl = document.getElementById('dpr-crew-dist');
              if (!tbl || tbl.__dprBldgBound) return;
              tbl.__dprBldgBound = true;
              tbl.addEventListener('click', function(e) {
                var el = e.target.closest('.dpr-bldg-link');
                if (!el) return;
                var bldg = el.getAttribute('data-bldg');
                if (bldg) {
                  window.__dprClickBldg = bldg;
                  // Emit a synthetic event NiceGUI can catch via the
                  // window — but simpler, call the emit method directly.
                  if (window.emitEvent) {
                    window.emitEvent('dpr_bldg_click', {bldg: bldg});
                  }
                }
              });
            })();
            """
        )

        # Register a client-side event handler bridge
        ui.on("dpr_bldg_click", _handle_bldg_click, [])

    # ── Activity breakdown — item 11: remove Rows; new column set ───
    if s["activities"]:
        total_crew = s["total_crew"] or 1
        rows = ""
        for a in s["activities"]:
            pct = a["crew"] / total_crew * 100
            rows += (
                f'<tr>'
                f'<td>{escape(str(a["activity"]))}</td>'
                f'<td class="num">{a["buildings"]}</td>'
                f'<td class="crew">{a["crew"]}</td>'
                f'<td class="num">{pct:.0f}%</td>'
                f'</tr>'
            )
        ui.html(
            f'<div class="dpr-sum-card">'
            f'  <div class="dpr-sum-title">Activity breakdown</div>'
            f'  <div style="overflow-x:auto;">'
            f'  <table class="dpr-sum-table">'
            f'    <thead><tr>'
            f'      <th>Activity</th>'
            f'      <th class="num">No. of Buildings</th>'
            f'      <th class="num">Crew. No</th>'
            f'      <th class="num">Percentage%</th>'
            f'    </tr></thead>'
            f'    <tbody>{rows}</tbody>'
            f'  </table></div>'
            f'</div>'
        )

    # ── Decision flags — items 10 & 11 interactive ───────────────────
    _render_decision_flags(rpt, s)


def _render_decision_flags(rpt, s: dict) -> None:
    """Render `structured_flags` as clickable cards (item 10, 11)."""
    flags = s.get("structured_flags", [])

    with ui.element("div").classes("dpr-sum-card"):
        ui.html('<div class="dpr-sum-title">Decision flags</div>')

        if not flags:
            ui.html(
                '<div style="color:#F2740C;font-size:12px;'
                'line-height:1.55;">'
                'No flags raised. Data is clean and consistent across '
                'sources.</div>'
            )
            return

        for flag in flags:
            kind = flag.get("kind")
            label = flag.get("label", "")

            if kind == "hard_conflicts":
                # Clickable
                with ui.element("div").classes("dpr-flag-card danger").on(
                    "click", lambda _e=None, c=flag["conflicts"]:
                        _open_conflict_modal(rpt, c)
                ):
                    ui.html(f'<div class="dpr-flag-label">{escape(label)}</div>')
                    ui.html('<div class="dpr-flag-action">Review ›</div>')

            elif kind == "unify_headers":
                with ui.element("div").classes("dpr-flag-card warn").on(
                    "click", lambda _e=None: _open_unify_headers_modal(rpt)
                ):
                    ui.html(f'<div class="dpr-flag-label">{escape(label)}</div>')
                    ui.html('<div class="dpr-flag-action">Review ›</div>')

            elif kind == "quality_score":
                ui.html(
                    f'<div class="dpr-flag-card">'
                    f'  <div class="dpr-flag-label">'
                    f'    {escape(label)}</div>'
                    f'</div>'
                )

            elif kind == "info":
                for item in flag.get("items", []):
                    ui.html(
                        f'<div class="dpr-flag-card info">'
                        f'  <div class="dpr-flag-label" '
                        f'       style="color:#c8c8cc;">{escape(item)}</div>'
                        f'</div>'
                    )


# ═══════════════════════════════════════════════════════════════════════════
# Overview tab — items 21, 22
# ═══════════════════════════════════════════════════════════════════════════
def _overview_tab(rpt, mp, act, prog):
    from core.normalize import to_float as _tf

    # Activity crew aggregation (item 21: no row count)
    act_crew: dict[str, int] = {}
    act_bldgs: dict[str, set] = {}
    for r in rpt.work_progress:
        a = (r.get("activity") or "").strip()
        if not a:
            continue
        sk = int(_tf(r.get("skilled")) or 0)
        hp = int(_tf(r.get("helpers")) or 0)
        act_crew[a] = act_crew.get(a, 0) + sk + hp
        b = (r.get("building") or "").strip()
        if b:
            act_bldgs.setdefault(a, set()).add(b)

    act_items = sorted(act_crew.items(), key=lambda kv: -kv[1])[:10]
    total_places = sum(len(v) for v in act_bldgs.values())

    # Item 22 — Crew Composition: top-20 rectangles
    s = SUM.compute(rpt)
    buildings = s.get("buildings", [])

    with ui.element("div").classes("dpr-grid"):
        with panel("Manpower by Building",
                   subtitle="Skilled + assistant headcount per building.",
                   total=A.fmt_count(mp.total), total_label="workers"):
            if mp.by_building:
                bar_list(mp.by_building[:10], show_pct=True)
            else:
                ui.html('<div class="dpr-panel-empty">No manpower.</div>')

        with panel("Activity Breakdown",
                   subtitle="Crew per activity.",
                   total=A.fmt_count(total_places),
                   total_label="No. Of Places Active Now"):
            if act_items:
                bar_list(act_items, show_pct=True)
            else:
                ui.html('<div class="dpr-panel-empty">No activities.</div>')

        with panel("Progress Distribution",
                   subtitle="Tasks per completion band.",
                   total=f"{prog.reported}", total_label="reported"):
            if prog.reported:
                histogram(prog.buckets)
            else:
                ui.html('<div class="dpr-panel-empty">No progress values.</div>')

        # Item 22 — Crew Composition as rectangles
        with panel("Crew Composition",
                   subtitle="Top 20 buildings by assistant count.",
                   total=A.fmt_count(sum(b.get("assistants", 0)
                                         for b in buildings)),
                   total_label="assistants"):
            crew_rectangles(
                buildings,
                on_click=lambda b: _open_building_detail_modal(rpt, b),
                limit=20,
            )


# ═══════════════════════════════════════════════════════════════════════════
# Layout tab — item 23
# ═══════════════════════════════════════════════════════════════════════════
def _layout_tab(rpt):
    matx = A.activity_matrix(rpt, top_n_acts=6)
    zones = A.zone_density(rpt)
    if matx["activities"] and matx["buildings"]:
        with ui.element("div").classes("dpr-grid"):
            with panel("Building × Activity Matrix",
                       subtitle="Where each trade is deployed.", wide=True):
                matrix_view(matx)
    if zones:
        with ui.element("div").classes("dpr-grid"):
            with panel("Zone Density",
                       subtitle="Work rows by zone.",
                       total=A.fmt_count(sum(c for _, c in zones)),
                       total_label="rows", wide=True):
                top_list([(f"Zone {z}", c) for z, c in zones])


# ═══════════════════════════════════════════════════════════════════════════
# Quality tab — unchanged
# ═══════════════════════════════════════════════════════════════════════════
def _quality_tab(rpt, q):
    with ui.element("div").classes("dpr-grid"):
        with panel("Data Quality Breakdown",
                   subtitle="Four-dimension composite.",
                   total=f"{q.score}", total_label="score"):
            bars = [
                ("Completeness",  q.completeness  * 100, 40),
                ("Confidence",    q.confidence    * 100, 30),
                ("Corroboration", q.corroboration * 100, 15),
                ("Consistency",   q.consistency   * 100, 15),
            ]
            rows_html = ""
            for label, pct, weight in bars:
                rows_html += (
                    f'<div class="dpr-bar-row">'
                    f'  <span class="dpr-bar-label">{label} '
                    f'    <span style="color:#4f4f56;font-size:9.5px;">'
                    f'({weight}%)</span></span>'
                    f'  <div class="dpr-bar-track">'
                    f'    <div class="dpr-bar-fill" style="width:{pct:.1f}%"></div>'
                    f'  </div>'
                    f'  <span class="dpr-bar-value">{pct:.0f}%</span>'
                    f'</div>'
                )
            ui.html(f'<div class="dpr-bars">{rows_html}</div>')

        with panel("Field Coverage",
                   subtitle="Percent of work rows containing each field.",
                   total=f"{len(rpt.work_progress)}", total_label="rows"):
            from core import anomaly as AN
            cov = AN.compute_coverage(rpt)
            html = '<div class="dpr-bars">'
            for f in cov["fields"]:
                pct = f["pct"]
                tone = ("#F2740C" if pct >= 75
                        else "#ffb020" if pct >= 40 else "#ff4d6a")
                html += (
                    f'<div class="dpr-bar-row">'
                    f'  <span class="dpr-bar-label">{f["label"]}</span>'
                    f'  <div class="dpr-bar-track">'
                    f'    <div class="dpr-bar-fill" '
                    f'         style="width:{pct:.1f}%;background:{tone};"></div>'
                    f'  </div>'
                    f'  <span class="dpr-bar-value">{f["count"]}/{f["total"]}'
                    f'    <span class="dpr-bar-pct">{pct:.0f}%</span></span>'
                    f'</div>'
                )
            html += "</div>"
            ui.html(html)


# ═══════════════════════════════════════════════════════════════════════════
# Detailed tab — unchanged
# ═══════════════════════════════════════════════════════════════════════════
def _detailed_tab(rpt):
    mats = A.materials_top(rpt, 20)
    equip = A.equipment_status(rpt)
    with ui.element("div").classes("dpr-grid"):
        with panel("Top Materials",
                   subtitle="Materials by quantity.",
                   total=f"{len(mats)}", total_label="items"):
            if mats:
                top_list([
                    (n, f"{int(q) if q.is_integer() else q:g} {u}".strip())
                    for n, q, u in mats
                ])
            else:
                ui.html('<div class="dpr-panel-empty">No materials.</div>')

        with panel("Equipment Status",
                   subtitle="Equipment by status.",
                   total=A.fmt_count(sum(c for _, c in equip)) if equip else "",
                   total_label="units"):
            if equip:
                bar_list(equip, show_pct=True)
            else:
                ui.html('<div class="dpr-panel-empty">No equipment.</div>')

    with ui.card().classes("dpr-card w-full"):
        section_title("Detailed Report", "Complete breakdown by section.")
        report_preview()


# ═══════════════════════════════════════════════════════════════════════════
# Production panel — targets dialog still reachable
# ═══════════════════════════════════════════════════════════════════════════
def _render_production_panel(rpt):
    acts = sorted({
        (r.get("activity") or "").strip()
        for r in rpt.work_progress if r.get("activity")
    })
    targets = state.s_curve_targets()
    chart_container = ui.column().classes("w-full gap-2")

    def _refresh_chart():
        chart_container.clear()
        with chart_container:
            if not targets:
                ui.html('<div class="dpr-panel-empty">'
                        'No targets set yet.</div>')
                return
            try:
                recent = HIST.load_recent(60)
            except Exception as e:
                ui.html(f'<div class="dpr-panel-empty">'
                        f'Could not load history: {e}</div>')
                return
            if not recent:
                ui.html('<div class="dpr-panel-empty">'
                        'No saved reports yet.</div>')
                return
            for act, cfg in targets.items():
                curve = PROD.build_curve(
                    act, recent,
                    target_total=cfg["target"],
                    start_date=cfg["start"],
                    end_date=cfg["end"],
                )
                if not curve["x_labels"]:
                    ui.html(f'<div class="dpr-panel-empty">'
                            f'No data for "{act}" in the target window.</div>')
                    continue
                var = curve["variance_pct"]
                tone = "#F2740C" if var >= 0 else "#ff4d6a"
                tgt = int(cfg["target"]) if float(cfg["target"]).is_integer() else cfg["target"]
                ui.html(
                    f'<div style="display:flex;align-items:baseline;'
                    f'gap:10px;margin-top:6px;flex-wrap:wrap;">'
                    f'  <span style="color:#e8e8ea;font-size:12.5px;'
                    f'      font-weight:600;">{act}</span>'
                    f'  <span style="color:#85858c;font-size:10.5px;">'
                    f'    target {tgt}</span>'
                    f'  <span style="color:{tone};font-size:11px;'
                    f'      font-weight:600;">'
                    f'    {var:+.1f}% vs plan</span>'
                    f'</div>'
                )
                line_chart(
                    f"{act} — cumulative",
                    [
                        {"name": "Planned", "color": "#4f4f56",
                         "points": [v for _, v in curve["planned"]]},
                        {"name": "Actual",  "color": "#F2740C",
                         "points": [v for _, v in curve["actual"]]},
                    ],
                    x_labels=curve["x_labels"],
                    height=200,
                )

    def _open_targets_dialog():
        with ui.dialog() as dlg, ui.card().classes("dpr-card").style(
            "min-width:340px;max-width:520px;"
        ):
            ui.label("S-Curve Targets").classes("dpr-title")
            ui.label("Set planned quantity and date range per activity.") \
                .classes("dpr-muted").style("margin-bottom:10px;font-size:11px;")

            act_select = ui.select(
                acts, label="Activity", value=(acts[0] if acts else None),
            ).props("outlined dense").classes("w-full")

            with ui.row().classes("w-full gap-2"):
                target_in = ui.number(
                    label="Target", value=100, min=0,
                ).props("outlined dense").classes("flex-1")
            with ui.row().classes("w-full gap-2"):
                start_in = ui.input(
                    label="Start (YYYY-MM-DD)",
                ).props("outlined dense").classes("flex-1")
                end_in = ui.input(
                    label="End (YYYY-MM-DD)",
                ).props("outlined dense").classes("flex-1")

            existing_container = ui.column().classes("w-full gap-1 mt-2")
            def _render_existing():
                existing_container.clear()
                with existing_container:
                    if not targets:
                        return
                    ui.label("Current targets").classes("dpr-muted")
                    for a, cfg in targets.items():
                        ui.label(f"• {a} — {cfg['target']} by {cfg['end']}") \
                            .classes("text-white").style("font-size:11px;")
            _render_existing()

            def _save():
                if not act_select.value:
                    ui.notify("Select an activity", color="orange"); return
                try:
                    t = float(target_in.value or 0)
                except (TypeError, ValueError):
                    ui.notify("Target must be a number", color="orange"); return
                if not start_in.value or not end_in.value:
                    ui.notify("Start and end date required", color="orange"); return
                state.set_s_curve_target(
                    act_select.value, t, start_in.value, end_in.value,
                )
                _refresh_chart()
                _render_existing()
                ui.notify(f"Saved target for {act_select.value}", color="green")

            with ui.row().classes("gap-2 mt-3"):
                ui.button("Save", on_click=_save).classes("dpr-btn-primary dpr-btn-xs")
                ui.button("Clear all", on_click=lambda: (
                    state.clear_s_curve_targets(),
                    _refresh_chart(), _render_existing(),
                    ui.notify("Cleared", color="orange"),
                )).classes("dpr-btn-xs")
                ui.button("Close", on_click=dlg.close).classes("dpr-btn-xs")

        dlg.open()

    with ui.element("div").classes("dpr-panel dpr-panel-wide"):
        with ui.element("div").classes("dpr-panel-header"):
            ui.html('<div class="dpr-panel-title">Production Curve</div>')
            ui.button("Set targets",
                      on_click=_open_targets_dialog).classes(
                "dpr-btn-xs")
        ui.html(
            '<div class="dpr-panel-sub">'
            'Planned vs actual cumulative quantity per activity, from the '
            'last 60 saved reports. Plan follows a standard S-curve.'
            '</div>'
        )
        _refresh_chart()


# ═══════════════════════════════════════════════════════════════════════════
# Main render
# ═══════════════════════════════════════════════════════════════════════════
def render():
    rpt = state.report()

    with page_shell(
        active="results",
        title="Report Dashboard",
        subtitle="Merged Daily Progress Report — normalized across all sources.",
    ):
        ui.add_head_html(_REPORT_CSS, shared=False)

        if rpt is None:
            _empty()
            return

        _hydrate_session_from_report()

        # ── Drawer + backdrop + toggle — item 19 ────────────────────
        backdrop = ui.element("div").classes("dpr-drawer-backdrop")

        drawer = ui.element("div").classes("dpr-drawer")
        with drawer:
            with ui.element("div").classes("dpr-drawer-head"):
                ui.html('<div class="dpr-drawer-title">Project details</div>')
                close_btn = ui.element("button").classes("dpr-drawer-close")
                with close_btn:
                    ui.html("✕")
            _render_project_details_body()

        toggle_btn = ui.element("button").classes("dpr-drawer-toggle")
        with toggle_btn:
            toggle_icon = ui.html("›")  # professional arrow, closed state

        drawer_state = {"open": False}

        def _open_drawer():
            drawer_state["open"] = True
            drawer.classes(add="open")
            backdrop.classes(add="open")
            toggle_icon.content = "‹"   # arrow rotated to close

        def _close_drawer():
            drawer_state["open"] = False
            drawer.classes(remove="open")
            backdrop.classes(remove="open")
            toggle_icon.content = "›"

        def _toggle_drawer():
            if drawer_state["open"]:
                _close_drawer()
            else:
                _open_drawer()

        toggle_btn.on("click", _toggle_drawer)
        close_btn.on("click", _close_drawer)
        backdrop.on("click", _close_drawer)

        # ── Main content ────────────────────────────────────────────
        with ui.element("div").classes("dpr-report-main"):
            _render_report_header(rpt)
            _download_row()

            # Item 18 — Zones board button next to the tabs
            with ui.element("div").classes("dpr-tabs-row"):
                with ui.tabs().classes("dpr-tabs").props("align=left") as tabs:
                    ui.tab("Summary",  icon="insights")
                    ui.tab("Overview", icon="dashboard")
                    ui.tab("Layout",   icon="grid_view")
                    ui.tab("Quality",  icon="verified")
                    ui.tab("Detailed", icon="table_view")
                ui.button(
                    "Zones board",
                    on_click=lambda: ui.navigate.to("/zones"),
                    icon="map",
                ).classes("dpr-zones-tab")

            with ui.tab_panels(tabs, value="Summary").classes(
                "w-full"
            ).style("background: transparent; padding: 0;"):
                with ui.tab_panel("Summary").style("padding: 12px 0 0 0;"):
                    _summary_tab(rpt)
                with ui.tab_panel("Overview").style("padding: 12px 0 0 0;"):
                    mp = A.manpower(rpt)
                    act = A.activities(rpt)
                    prog = A.progress(rpt)
                    _overview_tab(rpt, mp, act, prog)
                with ui.tab_panel("Layout").style("padding: 12px 0 0 0;"):
                    _layout_tab(rpt)
                with ui.tab_panel("Quality").style("padding: 12px 0 0 0;"):
                    q = Q.compute_quality(rpt)
                    _quality_tab(rpt, q)
                with ui.tab_panel("Detailed").style("padding: 12px 0 0 0;"):
                    _detailed_tab(rpt)

            # Production panel accessible below the tabs
            _render_production_panel(rpt)


def _empty() -> None:
    n_queue = len(state.queue_files())
    with ui.card().classes("dpr-card w-full"):
        ui.label("No report in this session.").classes("dpr-title text-xl")
        if n_queue == 0:
            ui.label("No files uploaded. Add at least one PDF / XLSX / PNG / "
                     "JPG / TXT, then click Aggregate.").classes("text-white")
        else:
            ui.label(f"{n_queue} file(s) queued but no report produced. "
                     "Check the Activity Log.").classes("text-white")

    if state.logs():
        section_title("Last activity", "Recent log lines.")
        with ui.card().classes("dpr-card w-full"):
            ui.html("<br>".join(state.logs()[-15:])).classes("dpr-console w-full")

    with ui.row().classes("gap-3 mt-2"):
        ui.button("Back to Upload", on_click=lambda: ui.navigate.to("/"))
