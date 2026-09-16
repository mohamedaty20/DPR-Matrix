"""Results — analytics dashboard."""
from __future__ import annotations

import re

from nicegui import ui

from core import analytics as A
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

        # ── Metadata ──────────────────────────────────────────────────
        metadata_strip([
            ("Project",     rpt.project_name or "—"),
            ("Date",        rpt.report_date  or "—"),
            ("Location",    rpt.site_location or "—"),
            ("Prepared by", rpt.prepared_by  or "—"),
            ("Weather",     rpt.weather      or "—"),
            ("Shift",       rpt.shift        or "—"),
        ])

        # ── Download bar (top) ────────────────────────────────────────
        _download_row(prominent=True)

        # ── Compute analytics ─────────────────────────────────────────
        mp   = A.manpower(rpt)
        act  = A.activities(rpt)
        prog = A.progress(rpt)
        eff  = A.crew_efficiency(rpt)
        zones = A.zone_density(rpt)
        mats = A.materials_top(rpt)
        equip = A.equipment_status(rpt)
        matx = A.activity_matrix(rpt, top_n_acts=6)
        sev = A.conflict_severity(rpt)

        # ── Stat grid ─────────────────────────────────────────────────
        stat_grid([
            {
                "label": "Source Files",
                "value": len(rpt.source_files),
                "sub":   "merged into this report",
                "tone":  "primary",
            },
            {
                "label": "Active Tasks",
                "value": len(rpt.work_progress),
                "sub":   f"{A.fmt_count(mp.buildings_with_crew)} building(s) · "
                         f"{act.distinct} activities",
            },
            {
                "label": "Total Manpower",
                "value": A.fmt_count(mp.total),
                "sub":   f"{mp.skilled} skilled · {mp.helpers} helpers",
            },
            {
                "label": "Avg Progress",
                "value": A.fmt_pct(prog.avg_pct) if prog.reported else "—",
                "sub":   (f"{prog.reported}/{prog.total_rows} rows reported"
                          if prog.reported else "no progress values in source"),
            },
            {
                "label": "Data Conflicts",
                "value": len(rpt.conflicts),
                "sub":   ("sources disagree — see banner"
                          if rpt.conflicts else "no disagreements"),
                "tone":  "danger" if rpt.conflicts else "primary",
            },
            {
                "label": "Peak Building",
                "value": mp.peak_building,
                "sub":   f"{mp.peak_building_count} crew on site",
                "tone":  "primary" if mp.peak_building_count else "",
            },
        ])

        # ── Row 1: manpower + activities ──────────────────────────────
        with ui.element("div").classes("dpr-grid"):
            with panel(
                "Manpower by Building",
                subtitle="Skilled + helper headcount per building — "
                         "shows where crew is concentrated today.",
                total=A.fmt_count(mp.total),
                total_label="workers",
            ):
                if mp.by_building:
                    bar_list(mp.by_building[:10], unit="", show_pct=True)
                else:
                    ui.html('<div class="dpr-panel-empty">'
                            'No manpower recorded in this report.</div>')

            with panel(
                "Activity Breakdown",
                subtitle="Number of building & floor locations per activity — "
                         "shows how widespread each trade is today.",
                total=A.fmt_count(act.total_locations),
                total_label="locations",
            ):
                if act.by_activity:
                    bar_list(act.by_activity[:10], show_pct=True)
                else:
                    ui.html('<div class="dpr-panel-empty">'
                            'No activities recorded in this report.</div>')

        # ── Row 2: progress histogram + crew ratio ────────────────────
        with ui.element("div").classes("dpr-grid"):
            with panel(
                "Progress Distribution",
                subtitle="How many tasks fall in each completion band. "
                         "Buckets are driven by the progress_pct field.",
                total=f"{prog.reported}",
                total_label="reported",
            ):
                if prog.reported:
                    histogram(prog.buckets)
                else:
                    ui.html('<div class="dpr-panel-empty">'
                            'No progress values reported in the source files.</div>')

            with panel(
                "Crew Composition",
                subtitle="Skilled vs helpers per building — "
                         "high helper ratio usually means more supervision needed.",
                total=A.fmt_count(mp.total),
                total_label="crew",
            ):
                if eff:
                    ratio_bars(eff[:8])
                else:
                    ui.html('<div class="dpr-panel-empty">'
                            'No crew data in this report.</div>')

        # ── Row 3: Building × Activity matrix (full width) ────────────
        if matx["activities"] and matx["buildings"]:
            with ui.element("div").classes("dpr-grid"):
                with panel(
                    "Building × Activity Matrix",
                    subtitle="Where each trade is deployed across the site. "
                             "Darker cells = more locations with that activity.",
                    wide=True,
                ):
                    matrix_view(matx)

        # ── Row 4: zones + materials + equipment ──────────────────────
        extra = bool(zones or mats or equip)
        if extra:
            with ui.element("div").classes("dpr-grid"):
                with panel(
                    "Zone Density",
                    subtitle="Work rows grouped by zone — top 8.",
                    total=A.fmt_count(sum(c for _, c in zones)) if zones else "",
                    total_label="rows",
                ):
                    if zones:
                        top_list([(f"Zone {z}", c) for z, c in zones])
                    else:
                        ui.html('<div class="dpr-panel-empty">'
                                'No zone data recorded.</div>')

                with panel(
                    "Top Materials",
                    subtitle="Materials by quantity across all sources.",
                    total=f"{len(mats)}",
                    total_label="items",
                ):
                    if mats:
                        top_list([
                            (f"{n} · {int(q) if q.is_integer() else q:g} {u}".strip(),
                             f"{int(q) if q.is_integer() else q:g} {u}".strip())
                            for n, q, u in mats
                        ])
                    else:
                        ui.html('<div class="dpr-panel-empty">'
                                'No materials with quantities recorded.</div>')

                with panel(
                    "Equipment Status",
                    subtitle="Equipment rows grouped by status.",
                    total=A.fmt_count(sum(c for _, c in equip)) if equip else "",
                    total_label="units",
                ):
                    if equip:
                        bar_list(equip, show_pct=True)
                    else:
                        ui.html('<div class="dpr-panel-empty">'
                                'No equipment status recorded.</div>')

        # ── Conflicts + notes ─────────────────────────────────────────
        from ui.conflicts import conflict_banner, notes_banner
        conflict_banner(rpt.conflicts)
        notes_banner(rpt.notes)

        # ── Detailed report ───────────────────────────────────────────
        with ui.card().classes("dpr-card w-full"):
            section_title(
                "Detailed Report",
                "Complete breakdown by section — work progress, equipment, "
                "materials, personnel, safety and quality.",
            )
            report_preview()

        # ── Download bar (bottom) + footer ────────────────────────────
        _download_row()

        with ui.row().classes("gap-3 mt-2 items-center"):
            if state.report_id():
                ui.label(f"Saved as report #{state.report_id()}") \
                    .classes("dpr-muted")


def _empty() -> None:
    n_queue = len(state.queue_files())
    with ui.card().classes("dpr-card w-full"):
        ui.label("No report in this session.").classes("dpr-title text-xl")
        if n_queue == 0:
            ui.label("No files uploaded. Add at least one PDF / XLSX / PNG / "
                     "JPG / TXT, then click Aggregate.").classes("text-white")
        else:
            ui.label(f"{n_queue} file(s) queued but no report produced. "
                     "The job may have been cancelled or failed — check the "
                     "Activity Log on the upload page.").classes("text-white")

    if state.logs():
        section_title("Last activity", "Recent log lines from this session.")
        with ui.card().classes("dpr-card w-full"):
            ui.html("<br>".join(state.logs()[-15:])).classes("dpr-console w-full")

    with ui.row().classes("gap-3 mt-2"):
        ui.button("Back to Upload", on_click=lambda: ui.navigate.to("/"))
