"""Results — report dashboard with right-side project details drawer."""
from __future__ import annotations

import base64
import re

from nicegui import ui, run

from core import analytics as A
from core import quality as Q
from core import risk as RISK
from core import production as PROD
from core import history as HIST
from core.db import update_report_payload
from ui import state
from ui.shell import page_shell
from ui.components import (
    bar_list,
    histogram,
    line_chart,
    matrix_view,
    panel,
    ratio_bars,
    report_preview,
    risk_forecast,
    section_title,
    stat_grid,
    top_list,
)


# ═══════════════════════════════════════════════════════════════════════════
# Page CSS — drawer, header, tabs
# ═══════════════════════════════════════════════════════════════════════════
_REPORT_CSS = """
<style>
/* ── Floating toggle button (fixed, top-right, below topbar) ──────── */
.dpr-drawer-toggle {
  position: fixed;
  top: 62px;
  right: 16px;
  z-index: 45;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: #0c0c0f;
  border: 1px solid rgba(34,197,94,0.42);
  color: #22c55e;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  line-height: 1;
  padding: 0;
  box-shadow: 0 2px 14px rgba(0,0,0,0.55);
  transition: border-color .15s ease, background .15s ease;
}
.dpr-drawer-toggle:hover {
  border-color: rgba(34,197,94,0.85);
  background: rgba(34,197,94,0.06);
}
.dpr-drawer-toggle .dpr-drawer-toggle-label {
  margin-left: 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

/* ── Drawer (slides in from right) ────────────────────────────────── */
.dpr-drawer {
  position: fixed;
  top: 0;
  right: 0;
  height: 100vh;
  width: 340px;
  max-width: 92vw;
  background: linear-gradient(180deg, #0c0c0f 0%, #06060a 100%);
  border-left: 1px solid rgba(34,197,94,0.28);
  box-shadow: -10px 0 40px rgba(0,0,0,0.7);
  transform: translateX(105%);
  transition: transform .22s ease;
  z-index: 70;
  overflow-y: auto;
  padding: 16px 16px 28px 16px;
  -webkit-overflow-scrolling: touch;
}
.dpr-drawer.open { transform: translateX(0); }

/* ── Backdrop (dim, click to close) ───────────────────────────────── */
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

/* ── Drawer header ────────────────────────────────────────────────── */
.dpr-drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(34,197,94,0.18);
  gap: 8px;
}
.dpr-drawer-title {
  color: #22c55e;
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-weight: 700;
}
.dpr-drawer-close {
  background: transparent;
  color: #85858c;
  border: 1px solid rgba(34,197,94,0.28);
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
  color: #22c55e;
  border-color: rgba(34,197,94,0.7);
}

/* ── Project fields ───────────────────────────────────────────────── */
.dpr-proj-logo {
  width: 100%;
  max-height: 80px;
  object-fit: contain;
  display: block;
  margin-bottom: 10px;
  border-radius: 6px;
  background: #050506;
  padding: 8px;
  border: 1px solid rgba(34,197,94,0.18);
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

/* ── Report header (in main flow) ─────────────────────────────────── */
.dpr-report-main {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
  width: 100%;
}
.dpr-report-header {
  background: linear-gradient(180deg, #0c0c0f 0%, #08080a 100%);
  border: 1px solid rgba(34,197,94,0.20);
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
.dpr-report-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(34,197,94,0.10);
}
.dpr-mini-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  background: rgba(34,197,94,0.08);
  border: 1px solid rgba(34,197,94,0.20);
  border-radius: 999px;
  font-size: 10.5px;
  color: #85858c;
  font-weight: 600;
}
.dpr-mini-pill b { color: #e8e8ea; font-weight: 700; }

.dpr-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}
.dpr-btn-xs.q-btn {
  min-height: 26px !important;
  height: 26px !important;
  padding: 0 10px !important;
  font-size: 11px !important;
  font-weight: 600 !important;
}

/* ── Compact tabs ─────────────────────────────────────────────────── */
.dpr-tabs .q-tab {
  min-height: 34px !important;
  padding: 0 10px !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
  font-size: 11.5px !important;
  font-weight: 600 !important;
}
.dpr-tabs .q-tab__label { font-size: 11.5px !important; }
.dpr-tabs .q-tab__icon { font-size: 16px !important; }
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
    with ui.element("div").classes("dpr-download-bar"):
        with ui.element("div").classes("dpr-download-bar-label"):
            ui.html(f"Download report<small>{_stem()}.pdf · .xlsx · .txt</small>")
        with ui.row().classes("gap-2 items-center"):
            ui.button("PDF",   on_click=_download_pdf).classes("dpr-btn-primary")
            ui.button("Excel", on_click=_download_excel)
            ui.button("TXT",   on_click=_download_txt)


# ═══════════════════════════════════════════════════════════════════════════
# Project details <-> report sync
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


# ═══════════════════════════════════════════════════════════════════════════
# Drawer content (project details)
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

    _field("project_name", "Project name", "e.g. WTG Foundation Package")
    _field("location",     "Location",     "e.g. Ras Ghareb, Zone B")
    _field("company_name", "Company name", "e.g. Orascom Construction")
    _field("contractor",   "Contractor / Sub", "e.g. Hassan Allam")
    _field("consultant",   "Consultant",   "e.g. Dar Al-Handasah")
    _field("weather",      "Weather",      "e.g. Clear, 34°C")
    _field("shift",        "Shift",        "e.g. Day")

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
# Report header
# ═══════════════════════════════════════════════════════════════════════════
def _render_report_header(rpt, on_reconcile, on_targets):
    with ui.element("div").classes("dpr-report-header"):
        ui.html('<div style="color:#22c55e;font-size:10.5px;'
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

        q = Q.compute_quality(rpt)
        with ui.element("div").classes("dpr-report-meta-row"):
            ui.html(
                f'<span class="dpr-mini-pill">'
                f'Report <b>#{state.report_id() or "—"}</b></span>'
                f'<span class="dpr-mini-pill">'
                f'<b>{len(rpt.work_progress)}</b> work rows</span>'
                f'<span class="dpr-mini-pill">'
                f'Quality <b>{q.grade}</b> ({q.score}/100)</span>'
                f'<span class="dpr-mini-pill">'
                f'<b>{len(rpt.source_files)}</b> source file(s)</span>'
                f'<span class="dpr-mini-pill">'
                f'<b>{len(rpt.conflicts)}</b> conflict(s)</span>'
            )

        with ui.element("div").classes("dpr-action-row"):
            ui.button("Reconcile Sources", on_click=on_reconcile).classes(
                "dpr-btn-xs"
            )
            ui.button("Set targets", on_click=on_targets).classes("dpr-btn-xs")
            ui.button("Zones board",
                      on_click=lambda: ui.navigate.to("/zones")).classes(
                "dpr-btn-xs"
            )


# ═══════════════════════════════════════════════════════════════════════════
# Risk section
# ═══════════════════════════════════════════════════════════════════════════
def _render_risk_section():
    cache_key = f"{state.report_id()}:7"
    cached = state.risk_cache().get(cache_key)
    container = ui.column().classes("w-full gap-2")

    async def run_analysis():
        container.clear()
        with container:
            ui.label("Analyzing last 7 days with Gemini…").classes("dpr-muted")
        try:
            recent = await run.io_bound(HIST.load_recent, 7)
            data = await run.io_bound(RISK.analyze, recent)
            state.set_risk_cache(cache_key, data)
            state.log(f"[risk] {data.get('overall_risk','?')}")
            container.clear()
            with container:
                risk_forecast(data)
        except Exception as ex:
            state.log(f"[err] risk: {type(ex).__name__}: {ex}")
            container.clear()
            with container:
                ui.label(f"Risk analysis failed: {ex}").classes("text-white")

    with ui.element("div").classes("dpr-panel dpr-panel-wide"):
        with ui.element("div").classes("dpr-panel-header"):
            ui.html('<div class="dpr-panel-title">'
                    'Risk &amp; Bottleneck Forecast</div>')
            ui.button("Run analysis" if not cached else "Refresh",
                      on_click=run_analysis).classes("dpr-btn-primary dpr-btn-xs")
        ui.html(
            '<div class="dpr-panel-sub">'
            'Gemini reads the last 7 days of saved reports and flags schedule, '
            'quality, resource, weather, safety, and reporting risks.'
            '</div>'
        )
        with container:
            if cached:
                risk_forecast(cached)
            else:
                ui.html('<div class="dpr-panel-empty">'
                        'Click "Run analysis" to generate a forecast.</div>')


# ═══════════════════════════════════════════════════════════════════════════
# Production / S-curve
# ═══════════════════════════════════════════════════════════════════════════
_TARGETS_OPENER: dict = {"fn": lambda: None}


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
                        'No targets set. Click "Set targets" to add planned '
                        'quantities per activity.</div>')
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
                tone = "#22c55e" if var >= 0 else "#ff4d6a"
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
                        {"name": "Actual",  "color": "#22c55e",
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

    _TARGETS_OPENER["fn"] = _open_targets_dialog

    with ui.element("div").classes("dpr-panel dpr-panel-wide"):
        with ui.element("div").classes("dpr-panel-header"):
            ui.html('<div class="dpr-panel-title">Production Curve</div>')
        ui.html(
            '<div class="dpr-panel-sub">'
            'Planned vs actual cumulative quantity per activity, from the '
            'last 60 saved reports. Plan follows a standard S-curve.'
            '</div>'
        )
        _refresh_chart()


# ═══════════════════════════════════════════════════════════════════════════
# Tabs
# ═══════════════════════════════════════════════════════════════════════════
def _overview_tab(rpt, mp, act, prog):
    with ui.element("div").classes("dpr-grid"):
        with panel("Manpower by Building",
                   subtitle="Skilled + helper headcount per building.",
                   total=A.fmt_count(mp.total), total_label="workers"):
            if mp.by_building:
                bar_list(mp.by_building[:10], show_pct=True)
            else:
                ui.html('<div class="dpr-panel-empty">No manpower.</div>')

        with panel("Activity Breakdown",
                   subtitle="Locations per activity.",
                   total=A.fmt_count(act.total_locations),
                   total_label="locations"):
            if act.by_activity:
                bar_list(act.by_activity[:10], show_pct=True)
            else:
                ui.html('<div class="dpr-panel-empty">No activities.</div>')

        with panel("Progress Distribution",
                   subtitle="Tasks per completion band.",
                   total=f"{prog.reported}", total_label="reported"):
            if prog.reported:
                histogram(prog.buckets)
            else:
                ui.html('<div class="dpr-panel-empty">No progress values.</div>')

        with panel("Crew Composition",
                   subtitle="Skilled vs helpers per building.",
                   total=A.fmt_count(mp.total), total_label="crew"):
            eff = A.crew_efficiency(rpt)
            if eff:
                ratio_bars(eff[:8])
            else:
                ui.html('<div class="dpr-panel-empty">No crew data.</div>')


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
                tone = ("#22c55e" if pct >= 75
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

        # ── Drawer + backdrop + toggle (all fixed-position, no scroll) ──
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
            toggle_icon = ui.html("☰")

        # ── Drawer open/close ────────────────────────────────────────
        drawer_state = {"open": False}

        def _open_drawer():
            drawer_state["open"] = True
            drawer.classes(add="open")
            backdrop.classes(add="open")
            toggle_icon.content = "✕"

        def _close_drawer():
            drawer_state["open"] = False
            drawer.classes(remove="open")
            backdrop.classes(remove="open")
            toggle_icon.content = "☰"

        def _toggle_drawer():
            if drawer_state["open"]:
                _close_drawer()
            else:
                _open_drawer()

        toggle_btn.on("click", _toggle_drawer)
        close_btn.on("click", _close_drawer)
        backdrop.on("click", _close_drawer)

        # ── Main content (full width) ────────────────────────────────
        with ui.element("div").classes("dpr-report-main"):
            def _open_reconcile():
                ui.navigate.to("/reconcile")

            def _open_targets():
                _TARGETS_OPENER["fn"]()

            _render_report_header(rpt, _open_reconcile, _open_targets)
            _download_row()

            mp = A.manpower(rpt)
            act = A.activities(rpt)
            prog = A.progress(rpt)
            q = Q.compute_quality(rpt)

            grade_tone = (
                "primary" if q.grade in ("A", "B")
                else "warning" if q.grade == "C"
                else "danger"
            )
            stat_grid([
                {"label": "Quality", "value": q.grade,
                 "sub": f"score {q.score}/100", "tone": grade_tone},
                {"label": "Work rows", "value": len(rpt.work_progress),
                 "sub": f"{A.fmt_count(mp.buildings_with_crew)} building(s) · "
                        f"{act.distinct} activities"},
                {"label": "Manpower", "value": A.fmt_count(mp.total),
                 "sub": f"{mp.skilled} skilled · {mp.helpers} helpers"},
                {"label": "Avg progress",
                 "value": A.fmt_pct(prog.avg_pct) if prog.reported else "—",
                 "sub": (f"{prog.reported}/{prog.total_rows} reported"
                         if prog.reported else "none reported")},
            ])

            _render_risk_section()
            _render_production_panel(rpt)

            with ui.tabs().classes("w-full dpr-tabs").props("align=left") as tabs:
                ui.tab("Overview", icon="dashboard")
                ui.tab("Layout",   icon="grid_view")
                ui.tab("Quality",  icon="verified")
                ui.tab("Detailed", icon="table_view")

            with ui.tab_panels(tabs, value="Overview").classes(
                "w-full"
            ).style("background: transparent; padding: 0;"):
                with ui.tab_panel("Overview").style("padding: 12px 0 0 0;"):
                    _overview_tab(rpt, mp, act, prog)
                with ui.tab_panel("Layout").style("padding: 12px 0 0 0;"):
                    _layout_tab(rpt)
                with ui.tab_panel("Quality").style("padding: 12px 0 0 0;"):
                    _quality_tab(rpt, q)
                with ui.tab_panel("Detailed").style("padding: 12px 0 0 0;"):
                    _detailed_tab(rpt)


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
