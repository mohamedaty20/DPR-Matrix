"""History — dashboard with stats, trend chart, and report list."""
from __future__ import annotations

from collections import Counter
from datetime import datetime

from nicegui import ui, run

from core.db import list_reports, get_report, delete_report, count_reports
from core import history as HIST
from ui import state
from ui.shell import page_shell
from ui.components import (
    line_chart,
    section_title,
    stat_grid,
    bar_list,
)


def render():
    with page_shell(
        active="history",
        title="Report History",
        subtitle=(
            "Every aggregated DPR stored in Turso. Click Open to reload a "
            "report into the current session, or Delete to remove it."
        ),
    ):
        container = ui.column().classes("w-full gap-3")

        async def refresh():
            container.clear()
            try:
                rows = await run.io_bound(list_reports, 200)
                total = await run.io_bound(count_reports)
                recent = await run.io_bound(HIST.load_recent, 30)
            except Exception as ex:
                with container:
                    ui.label(f"⚠ Database error: {ex}").classes("text-white")
                return

            with container:
                _render_dashboard(rows, total, recent)
                _render_list(rows, refresh)

        ui.timer(0.1, refresh, once=True)


def _render_dashboard(rows: list[dict], total: int, recent: list[dict]) -> None:
    if not rows:
        with ui.card().classes("dpr-card w-full"):
            ui.label("No reports yet.").classes("text-white")
            ui.label("Go to Upload, add at least one file, and click Aggregate.") \
                .classes("dpr-muted").style("margin-top:6px;")
        return

    # ── KPIs ──────────────────────────────────────────────────────────
    projects = {r.get("project_name") or "—" for r in rows}
    sites = {r.get("site_location") or "—" for r in rows}
    this_month = sum(
        1 for r in rows
        if (r.get("created_at") or "")[:7] == datetime.utcnow().strftime("%Y-%m")
    )
    total_work_rows = sum(
        len(e["report"].work_progress) for e in recent
    )
    total_manpower = 0
    for e in recent:
        for wr in e["report"].work_progress:
            from core.normalize import to_float
            total_manpower += int(to_float(wr.get("skilled")) or 0)
            total_manpower += int(to_float(wr.get("helpers")) or 0)

    stat_grid([
        {"label": "Total Reports", "value": total,
         "sub": f"across {len(projects)} project(s)", "tone": "primary"},
        {"label": "This Month", "value": this_month,
         "sub": f"of {total} total"},
        {"label": "Sites", "value": len(sites),
         "sub": ", ".join(sorted(sites)[:2])},
        {"label": "Work Rows (30d)", "value": total_work_rows,
         "sub": "aggregated rows in last 30 reports"},
    ])

    if not recent:
        return

    # ── Trend charts ─────────────────────────────────────────────────
    # Manpower per day (chronological)
    chronological = list(reversed(recent))
    x_labels: list[str] = []
    manpower_pts: list[float] = []
    rows_pts: list[float] = []
    for e in chronological:
        from core.normalize import to_float
        sk = hp = 0
        for wr in e["report"].work_progress:
            sk += int(to_float(wr.get("skilled")) or 0)
            hp += int(to_float(wr.get("helpers")) or 0)
        label = (e.get("report_date") or e.get("created_at", "")[:10])[-5:]
        x_labels.append(label)
        manpower_pts.append(float(sk + hp))
        rows_pts.append(float(len(e["report"].work_progress)))

    with ui.element("div").classes("dpr-grid"):
        line_chart(
            "Manpower over time",
            [{"name": "Total crew", "color": "#22c55e",
              "points": manpower_pts}],
            subtitle="Total skilled + helper headcount across recent reports.",
            x_labels=x_labels,
            height=220,
        )

        line_chart(
            "Work rows over time",
            [{"name": "Work rows", "color": "#22c55e",
              "points": rows_pts}],
            subtitle="Number of distinct building/floor/activity rows per report.",
            x_labels=x_labels,
            height=220,
        )

    # ── Projects bar ─────────────────────────────────────────────────
    project_counter = Counter(
        (r.get("project_name") or "—") for r in rows
    )
    top_projects = project_counter.most_common(8)
    if top_projects:
        with ui.element("div").classes("dpr-grid"):
            with ui.element("div").classes("dpr-panel dpr-panel-wide"):
                ui.html(
                    '<div class="dpr-panel-header">'
                    '  <div class="dpr-panel-title">Reports by project</div>'
                    '</div>'
                )
                bar_list(top_projects, show_pct=True)


def _render_list(rows: list[dict], refresh_cb) -> None:
    if not rows:
        return
    section_title("All reports", "Newest first.")
    for r in rows:
        _row(r, refresh_cb)


def _row(r: dict, refresh_cb):
    with ui.card().classes("dpr-card w-full").style("padding: 14px 16px !important;"):
        with ui.row().classes("w-full items-center justify-between gap-3 no-wrap"):
            with ui.column().classes("gap-0 flex-1"):
                ui.label(r.get("project_name") or "(unnamed project)") \
                    .classes("dpr-title text-lg")
                ui.label(
                    f"#{r['id']}  ·  {r.get('report_date') or '—'}  ·  "
                    f"{r.get('site_location') or '—'}"
                ).classes("text-white").style("font-size:12px;opacity:.7;")
                ui.label(f"Saved: {r.get('created_at','')}") \
                    .classes("text-white").style("font-size:11px;opacity:.5;")
            with ui.row().classes("gap-2"):
                ui.button("Open", on_click=lambda rid=r["id"]: _open(rid))
                ui.button("Delete",
                          on_click=lambda rid=r["id"]: _delete(rid, refresh_cb)) \
                    .classes("dpr-btn-danger")


async def _open(report_id: int):
    try:
        rpt = await run.io_bound(get_report, report_id)
        if rpt is None:
            ui.notify("Report not found", color="orange"); return
        state.set_report(rpt)
        state.set_report_id(report_id)
        state.log(f"[history] opened report #{report_id}")
        ui.navigate.to("/results")
    except Exception as ex:
        ui.notify(f"Failed to open: {ex}", color="red")


async def _delete(report_id: int, refresh_cb):
    try:
        await run.io_bound(delete_report, report_id)
        ui.notify(f"Deleted report #{report_id}", color="green")
        await refresh_cb()
    except Exception as ex:
        ui.notify(f"Delete failed: {ex}", color="red")
