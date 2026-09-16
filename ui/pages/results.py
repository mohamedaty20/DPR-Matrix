"""Results — analytics dashboard."""
from __future__ import annotations

import re

from nicegui import ui

from core import analytics as A
from core import quality as Q
from core import anomaly as AN
from ui import state
from ui.shell import page_shell
from ui.components import (
    bar_list,
    histogram,
    matrix_view,
    metadata_strip,
    panel,
    ratio_bars,
    report_preview,
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
# Coverage panel body
# ═══════════════════════════════════════════════════════════════════════════
def _render_coverage(report) -> None:
    cov = AN.compute_coverage(report)
    rows = cov["fields"]
    if not rows:
        ui.html('<div class="dpr-panel-empty">No rows to measure.</div>')
        return

    html = '<div class="dpr-bars">'
    for f in rows:
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

    missing = cov.get("missing_buildings") or []
    if missing:
        html += (
            f'<div style="margin-top:16px;padding-top:14px;'
            f'border-top:1px solid var(--dpr-border);">'
            f'  <div style="color:#ffb020;font-size:11.5px;font-weight:600;">'
            f'    ⚠ Buildings in personnel but not in work progress: '
            f'{", ".join(missing)}</div>'
            f'</div>'
        )
    ui.html(html).classes("w-full")


# ═══════════════════════════════════════════════════════════════════════════
# Anomaly panel body
# ═══════════════════════════════════════════════════════════════════════════
def _render_anomalies(anomalies: list[dict]) -> None:
    if not anomalies:
        ui.html('<div class="dpr-panel-empty">'
                'No statistical anomalies detected.</div>')
        return

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
            f'    <span class="dpr-toplist-value" '
            f'          style="color:#ffb020;">'
            f'{a.get("type","").replace("_"," ").title()}</span>'
            f'  </div>'
            f'  <div style="color:#85858c;font-size:11px;padding-left:18px;">'
            f'{a.get("reason","")}</div>'
            f'</div>'
        )
    html += "</div>"
    ui.html(html).classes("w-full")


# ═══════════════════════════════════════════════════════════════════════════
# Main
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

        # ── Metadata ──────────────────────────────────────────────────
        metadata_strip([
            ("Project",     rpt.project_name or "—"),
            ("Date",        rpt.report_date  or "—"),
            ("Location",    rpt.site_location or "—"),
            ("Prepared by", rpt.prepared_by  or "—"),
            ("Weather",     rpt.weather      or "—"),
            ("Shift",       rpt.shift        or "—"),
        ])

        _download_row(prominent=True)

        # ── Link to reconcile ─────────────────────────────────────────
        with ui.row().classes("gap-2 items-center mt-1"):
            ui.button(
                "Reconcile Sources →",
                on_click=lambda: ui.navigate.to("/reconcile"),
            ).classes("dpr-btn-primary")
            ui.label(
                f"{len(rpt.reconciliation)} merged key(s) with "
                f"per-source breakdown"
            ).classes("dpr-muted")

        # ── Analytics ─────────────────────────────────────────────────
        mp    = A.manpower(rpt)
        act   = A.activities(rpt)
        prog  = A.progress(rpt)
        eff   = A.crew_efficiency(rpt)
        zones = A.zone_density(rpt)
        mats  = A.materials_top(rpt)
        equip = A.equipment_status(rpt)
        matx  = A.activity_matrix(rpt, top_n_acts=6)

        # ── Stat grid ─────────────────────────────────────────────────
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

        # ── Row 1 ─────────────────────────────────────────────────────
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

        # ── Row 2: Quality + Coverage side by side ────────────────────
        with ui.element("div").classes("dpr-grid"):
            with panel("Data Quality Breakdown",
                       subtitle="Four-dimension composite. "
                                "A ≥85, B ≥70, C ≥55.",
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
                       subtitle="Percentage of work rows that contain "
                                "each field. Low coverage = sparse source data.",
                       total=f"{len(rpt.work_progress)}",
                       total_label="rows"):
                _render_coverage(rpt)

        # ── Row 3: Anomalies (full width) ─────────────────────────────
        if anomalies:
            with ui.element("div").classes("dpr-grid"):
                with panel(
                    "Anomalies",
                    subtitle="Statistical outliers in crew counts, "
                             "quantities, or coverage gaps.",
                    total=f"{len(anomalies)}",
                    total_label="flagged",
                    wide=True,
                ):
                    _render_anomalies(anomalies)

        # ── Row 4: progress + crew composition ────────────────────────
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

        # ── Row 5: matrix ─────────────────────────────────────────────
        if matx["activities"] and matx["buildings"]:
            with ui.element("div").classes("dpr-grid"):
                with panel("Building × Activity Matrix",
                           subtitle="Where each trade is deployed.",
                           wide=True):
                    matrix_view(matx)

        # ── Row 6: zones + materials + equipment ──────────────────────
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

        # ── Conflicts + notes ─────────────────────────────────────────
        from ui.conflicts import conflict_banner, notes_banner
        conflict_banner(rpt.conflicts)
        notes_banner(rpt.notes)

        # ── Detailed report ───────────────────────────────────────────
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
