from nicegui import ui, run
from ui import state
from ui.components import section_title
from core.db import list_reports, get_report, delete_report, count_reports
from core.errors import DPRMatrixError


def render():
    ui.label("Report History").classes("text-4xl font-bold dpr-title")
    ui.label("Every aggregated DPR stored in Turso. Click a row to reopen it.") \
        .classes("text-white mb-4")
    ui.separator()

    container = ui.column().classes("w-full gap-2")

    async def refresh():
        container.clear()
        try:
            rows = await run.io_bound(list_reports, 200)
            total = await run.io_bound(count_reports)
        except Exception as ex:
            with container:
                ui.label(f"⚠ Database error: {ex}").classes("text-red-400")
            return

        with container:
            ui.label(f"Total stored reports: {total}") \
                .classes("text-white").style("opacity:.7; font-size:12px")

            if not rows:
                ui.label("No reports yet. Go to Upload and aggregate one.") \
                    .classes("text-white")
                return

            for r in rows:
                _row(r)


    def _row(r: dict):
        with ui.card().classes("w-full"):
            with ui.row().classes("w-full items-center justify-between"):
                with ui.column().classes("gap-0"):
                    ui.label(r.get("project_name") or "(unnamed project)") \
                        .classes("dpr-title text-lg")
                    ui.label(
                        f"#{r['id']}  ·  {r.get('report_date') or '—'}  ·  "
                        f"{r.get('site_location') or '—'}"
                    ).classes("text-white").style("font-size:12px; opacity:.7")
                    ui.label(f"Saved: {r.get('created_at','')}") \
                        .classes("text-white").style("font-size:11px; opacity:.5")

                with ui.row().classes("gap-2"):
                    ui.button("Open", on_click=lambda rid=r["id"]: _open(rid))
                    ui.button("Delete", on_click=lambda rid=r["id"]: _delete(rid, refresh))


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


    # initial load + manual refresh
    ui.button("Refresh", on_click=refresh)
    ui.timer(0.1, refresh, once=True)
