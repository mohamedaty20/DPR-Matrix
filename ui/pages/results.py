"""Results — analytics dashboard with AI risk forecast and S-curve."""
from __future__ import annotations

import re

from nicegui import ui, run

from core import analytics as A
from core import quality as Q
from core import anomaly as AN
from core import risk as RISK
from core import production as PROD
from core import history as HIST
from ui import state
from ui.shell import page_shell
from ui.components import (
    bar_list,
    histogram,
    line_chart,
    matrix_view,
    metadata_strip,
    panel,
    ratio_bars,
    report_preview,
    risk_forecast,
    section_title,
    stat_grid,
    top_list,
)


def _safe(s: str, fallback: str = "report") -> str:
    s = (s or "").strip()
    s = re.sub(r"[^\w\-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or fallback


def _stem() -> str:
    rpt = state.report()
    if rpt is None:
        return "DPR_report"
    return (
        f"DPR_{_safe(rpt.project_name, 'project')}_"
        f"{_safe(rpt.report_date, '') or 'undated'}"
    )


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


def _download_row(*, prominent: bool = False) -> None:
    with ui.element("div").classes("dpr-download-bar"):
        with ui.element("div").classes("dpr-download-bar-label"):
            ui.html(f"Download report<small>{_stem()}.pdf · .xlsx · .txt</small>")
        with ui.row().classes("gap-2 items-center"):
            b = ui.button("Download PDF", on_click=_download_pdf)
            if prominent:
                b.classes("dpr-btn-primary")
            ui.button("Download Excel", on_click=_download_excel)
            ui.button("Download TXT",   on_click=_download_txt)


# ═══════════════════════════════════════════════════════════════════════════
# Risk Forecast panel
# ═══════════════════════════════════════════════════════════════════════════
def _render_risk_section(report_id, n_reports):
    cache_key = f"{report_id}:{n_reports}"
    cached = state.risk_cache().get(cache_key)

    container = ui.column().classes("w-full gap-2")

    def render_cached():
        container.clear()
        with container:
            if cached:
                risk_forecast(cached)

    async def run_analysis():
        container.clear()
        with container:
            ui.label("Analyzing last 7 days with Gemini…") \
                .classes("dpr-muted")
        try:
            recent = await run.io_bound(HIST.load_recent, 7)
            data = await run.io_bound(RISK.analyze, recent)
            state.set_risk_cache(cache_key, data)
            state.log(
                f"[risk] {data.get('overall_risk','?')} · "
                f"{len(data.get('risks', []))} risk(s)"
            )
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
            ui.button("Run AI analysis" if not cached else "Refresh",
                      on_click=run_analysis).classes("dpr-btn-primary")
        ui.html(
            '<div class="dpr-panel-sub">'
            'Gemini reads the last 7 days of reports and flags schedule, '
            'quality, resource, weather, safety, and reporting risks.'
            '</div>'
        )
        if cached:
            with container:
                risk_forecast(cached)
        else:
            with container:
                ui.html('<div class="dpr-panel-empty">'
                        'Click "Run AI analysis" to generate a risk forecast.'
                        '</div>')


# ═══════════════════════════════════════════════════════════════════════════
# Production / S-curve panel
# ═══════════════════════════════════════════════════════════════════════════
def _render_production_section(report):
    # Candidate activities from current report
    acts = sorted({
        (r.get("activity") or "").strip()
        for r in report.work_progress
        if r.get("activity")
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
            # Load recent history once, plot each target
            try:
                recent = HIST.load_recent(60)
            except Exception as e:
                ui.html(f'<div class="dpr-panel-empty">'
                        f'Could not load history: {e}</div>')
                return

            if not recent:
                ui.html('<div class="dpr-panel-empty">'
                        'No saved reports yet — aggregate and save one first.'
                        '</div>')
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
                ui.html(
                    f'<div style="display:flex;align-items:baseline;'
                    f'gap:10px;margin-top:6px;flex-wrap:wrap;">'
                    f'  <span style="color:#e8e8ea;font-size:13px;'
                    f'      font-weight:600;">{act}</span>'
                    f'  <span style="color:#85858c;font-size:11px;">'
                    f'    target {int(cfg["target"]) if float(cfg["target"]).is_integer() else cfg["target"]}'
                    f'  </span>'
                    f'  <span style="color:{tone};font-size:11.5px;'
                    f'      font-weight:600;">'
                    f'    {var:+.1f}% vs plan'
                    f'  </span>'
                    f'  <span style="color:#4f4f56;font-size:11px;">'
                    f'    today {curve["today_cum"]:.0f} / '
                    f'    {curve["today_planned"]:.0f} planned'
                    f'  </span>'
                    f'</div>'
                )
                line_chart(
                    f"{act} — cumulative curve",
                    [
                        {"name": "Planned", "color": "#4f4f56",
                         "points": [v for _, v in curve["planned"]]},
                        {"name": "Actual",  "color": "#22c55e",
                         "points": [v for _, v in curve["actual"]]},
                    ],
                    x_labels=curve["x_labels"],
                    height=220,
                )

    def _open_targets_dialog():
        with ui.dialog() as dlg, ui.card().classes("dpr-card").style(
            "min-width:520px;max-width:600px;"
        ):
            ui.label("S-Curve Targets").classes("dpr-title")
            ui.label(
                "Set planned quantity, start date, and end date per activity."
            ).classes("dpr-muted").style("margin-bottom:12px;")

            act_select = ui.select(
                acts, label="Activity", value=(acts[0] if acts else None),
            ).props("outlined dense").classes("w-full")

            with ui.row().classes("w-full gap-3"):
                target_in = ui.number(
                    label="Target quantity", value=100, min=0,
                ).props("outlined dense").classes("flex-1")
                start_in = ui.input(
                    label="Start date (YYYY-MM-DD)",
                ).props("outlined dense").classes("flex-1")
                end_in = ui.input(
                    label="End date (YYYY-MM-DD)",
                ).props("outlined dense").classes("flex-1")

            existing_container = ui.column().classes("w-full gap-1 mt-3")
            def _render_existing():
                existing_container.clear()
                with existing_container:
                    if not targets:
                        return
                    ui.label("Current targets").classes("dpr-muted")
                    for a, cfg in targets.items():
                        ui.label(
                            f"• {a} — {cfg['target']} by {cfg['end']}"
                        ).classes("text-white").style("font-size:11.5px;")
            _render_existing()

            def _save():
                if not act_select.value:
                    ui.notify("Select an activity", color="orange"); return
                try:
                    t = float(target_in.value or 0)
                except (TypeError, ValueError):
                    ui.notify("Target must be a number", color="orange"); return
                if not start_in.value or not end_in.value:
                    ui.notify("Start and end date required", color="orange")
                    return
                state.set_s_curve_target(
                    act_select.value, t, start_in.value, end_in.value,
                )
                _refresh_chart()
                _render_existing()
                ui.notify(f"Saved target for {act_select.value}", color="green")

            with ui.row().classes("gap-2 mt-4"):
                ui.button("Save target", on_click=_save).classes("dpr-btn-primary")
                ui.button("Clear all", on_click=lambda: (
                    state.clear_s_curve_targets(),
                    _refresh_chart(), _render_existing(),
                    ui.notify("Cleared", color="orange"),
                ))
                ui.button("Close", on_click=dlg.close)

        dlg.open()

    with ui.element("div").classes("dpr-panel dpr-panel-wide"):
        with ui.element("div").classes("dpr-panel-header"):
            ui.html('<div class="dpr-panel-title">Production Curve</div>')
            with ui.row().classes("gap-2"):
                ui.button("Set targets", on_click=_open_targets_dialog)
        ui.html(
            '<div class="dpr-panel-sub">'
            'Planned vs actual cumulative quantity per activity, from the '
            'last 60 saved reports. Plan follows a standard cosine S-curve.'
            '</div>'
        )
        _refresh_chart()


# ═══════════════════════════════════════════════════════════════════════════
# Main render
# ═══════════════════════════════════════════════════════════════════════════
def render():
    rpt = state.report()
    title = "Report Dashboard"
    subtitle = (
        "Merged Daily Progress Report — normalized across all sources, "
        "ready for engineer review and export."
    )

    with page_shell(active="results", title=title, subtitle=subtitle):
        if rpt is None:
            _empty()
            return

        q = Q.compute_quality(rpt)
        anomalies = AN.detect_anomalies(rpt)

        metadata_strip([
            ("Project",     rpt.project_name or "—"),
            ("Date",        rpt.report_date  or "—"),
            ("Location",    rpt.site_location or "—"),
            ("Prepared by", rpt.prepared_by  or "—"),
            ("Weather",     rpt.weather      or "—"),
            ("Shift",       rpt.shift        or "—"),
        ])

        _download_row(prominent=True)

        with ui.row().classes("gap-2 items-center mt-1"):
            ui.button(
                "Reconcile Sources →",
                on_click=lambda: ui.navigate.to("/reconcile"),
            ).classes("dpr-btn-primary")
            ui.label(
                f"{len(rpt.reconciliation)} merged key(s)"
            ).classes("dpr-muted")

        # ── NEW: AI Risk Forecast ─────────────────────────────────────
        _render_risk_section(state.report_id(), 7)

        # ── NEW: Production Curve / S-Curve ───────────────────────────
        _render_production_section(rpt)

        # ── Existing analytics ────────────────────────────────────────
        mp    = A.manpower(rpt)
        act   = A.activities(rpt)
        prog  = A.progress(rpt)
        eff   = A.crew_efficiency(rpt)
        zones = A.zone_density(rpt)
        mats  = A.materials_top(rpt)
        equip = A.equipment_status(rpt)
        matx  = A.activity_matrix(rpt, top_n_acts=6)

        grade_tone = (
            "primary" if q.grade in ("A", "B")
            else "warning" if q.grade == "C"
            else "danger"
        )
        stat_grid([
            {"label": "Data Quality", "value": q.grade,
             "sub": f"score {q.score}/100", "tone": grade_tone},
            {"label": "Source Files", "value": len(rpt.source_files),
             "sub": "merged into this report"},
            {"label": "Active Tasks", "value": len(rpt.work_progress),
             "sub": f"{A.fmt_count(mp.buildings_with_crew)} building(s) · "
                    f"{act.distinct} activities"},
            {"label": "Total Manpower", "value": A.fmt_count(mp.total),
             "sub": f"{mp.skilled} skilled · {mp.helpers} helpers"},
            {"label": "Avg Progress",
             "value": A.fmt_pct(prog.avg_pct) if prog.reported else "—",
             "sub": (f"{prog.reported}/{prog.total_rows} rows reported"
                     if prog.reported else "no progress values")},
            {"label": "Anomalies", "value": len(anomalies),
             "sub": "statistical outliers detected" if anomalies
                    else "none flagged",
             "tone": "warning" if anomalies else "primary"},
        ])

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
                        f'    <span style="color:#4f4f56;font-size:10px;">'
                        f'({weight}%)</span></span>'
                        f'  <div class="dpr-bar-track">'
                        f'    <div class="dpr-bar-fill" style="width:{pct:.1f}%"></div>'
                        f'  </div>'
                        f'  <span class="dpr-bar-value">{pct:.0f}%</span>'
                        f'</div>'
                    )
                ui.html(f'<div class="dpr-bars">{rows_html}</div>')

            with panel("Field Coverage",
                       subtitle="Percentage of work rows that contain each field.",
                       total=f"{len(rpt.work_progress)}", total_label="rows"):
                cov = AN.compute_coverage(rpt)
                html = '<div class="dpr-bars">'
                for f in cov["fields"]:
                    pct = f["pct"]
                    tone = "#22c55e" if pct >= 75 else "#ffb020" if pct >= 40 else "#ff4d6a"
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

        if anomalies:
            with ui.element("div").classes("dpr-grid"):
                with panel("Anomalies",
                           subtitle="Statistical outliers and coverage gaps.",
                           total=f"{len(anomalies)}", total_label="flagged",
                           wide=True):
                    html = '<div class="dpr-toplist">'
                    for a in anomalies:
                        b = a.get("building", "")
                        f = a.get("floor", "")
                        act = a.get("activity", "")
                        loc_bits = [x for x in (f"B{b}" if b else "",
                                                f"F{f}" if f else "",
                                                act) if x]
                        loc = " · ".join(loc_bits) or "—"
                        sev = a.get("severity", "soft")
                        dot = (
                            '<span class="dpr-ratio-dot" style="background:#ffb020"></span>'
                            if sev == "soft" else
                            '<span class="dpr-ratio-dot" style="background:#ff4d6a"></span>'
                        )
                        html += (
                            f'<div class="dpr-toplist-row" style="flex-direction:column;'
                            f'align-items:flex-start;gap:4px;">'
                            f'  <div style="display:flex;align-items:center;gap:8px;width:100%;">'
                            f'    {dot}'
                            f'    <span class="dpr-toplist-name" style="flex:1;">{loc}</span>'
                            f'    <span class="dpr-toplist-value" style="color:#ffb020;">'
                            f'{a.get("type","").replace("_"," ").title()}</span>'
                            f'  </div>'
                            f'  <div style="color:#85858c;font-size:11px;padding-left:18px;">'
                            f'{a.get("reason","")}</div>'
                            f'</div>'
                        )
                    html += "</div>"
                    ui.html(html)

        with ui.element("div").classes("dpr-grid"):
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
                if eff:
                    ratio_bars(eff[:8])
                else:
                    ui.html('<div class="dpr-panel-empty">No crew data.</div>')

        if matx["activities"] and matx["buildings"]:
            with ui.element("div").classes("dpr-grid"):
                with panel("Building × Activity Matrix",
                           subtitle="Where each trade is deployed.",
                           wide=True):
                    matrix_view(matx)

        if zones or mats or equip:
            with ui.element("div").classes("dpr-grid"):
                with panel("Zone Density",
                           subtitle="Work rows by zone.",
                           total=A.fmt_count(sum(c for _, c in zones)) if zones else "",
                           total_label="rows"):
                    if zones:
                        top_list([(f"Zone {z}", c) for z, c in zones])
                    else:
                        ui.html('<div class="dpr-panel-empty">No zone data.</div>')

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

        from ui.conflicts import conflict_banner, notes_banner
        conflict_banner(rpt.conflicts)
        notes_banner(rpt.notes)

        with ui.card().classes("dpr-card w-full"):
            section_title("Detailed Report", "Complete breakdown by section.")
            report_preview()

        _download_row()

        with ui.row().classes("gap-3 mt-2 items-center"):
            if state.report_id():
                ui.label(f"Saved as report #{state.report_id()}").classes("dpr-muted")


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
