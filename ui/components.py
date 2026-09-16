"""Reusable widgets."""
from __future__ import annotations
from nicegui import ui
from ui import state
from ui.conflicts import conflict_banner, notes_banner


def section_title(text: str) -> None:
    ui.label(text).classes("text-2xl font-bold dpr-title mt-4")


def log_console() -> ui.html:
    html = ui.html("").classes("dpr-console w-full")

    def refresh():
        html.content = "<br>".join(state.logs()[-80:]) or "— awaiting input —"

    ui.timer(1.0, refresh)
    refresh()
    return html


def _row_table(rows: list[dict]) -> None:
    if not rows:
        return
    # Union of keys, preserve order
    keys: list[str] = []
    for r in rows:
        for k in r.keys():
            if k not in keys:
                keys.append(k)

    headers = [k.replace("_", " ").title() for k in keys]
    table_rows = []
    for r in rows:
        cells = []
        for k in keys:
            v = r.get(k, "")
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v)
            cells.append(str(v))
        table_rows.append(cells)

    with ui.card().classes("w-full").style("padding:0"):
        ui.table(columns=[{"name": h, "label": h, "field": h, "align": "left"}
                          for h in headers],
                 rows=[dict(zip(headers, r)) for r in table_rows],
                 row_key=headers[0]).classes("w-full").props("flat dense")


def _bullet_list(items: list) -> None:
    if not items:
        return
    for it in items:
        if isinstance(it, dict):
            text = " · ".join(f"{k}: {v}" for k, v in it.items()
                              if v and k != "sources")
            srcs = it.get("sources") or []
            suffix = f"  [{', '.join(srcs)}]" if srcs else ""
            ui.label(f"• {text}{suffix}").classes("text-white")
        else:
            ui.label(f"• {it}").classes("text-white")


def report_preview() -> None:
    rpt = state.report()
    if rpt is None:
        ui.label("No report generated yet.").classes("text-white")
        return

    conflict_banner(rpt.conflicts)
    notes_banner(rpt.notes)

    def kv(label, value):
        if value:
            ui.label(label).classes("dpr-title")
            ui.label(str(value)).classes("text-white")

    kv("Project", rpt.project_name)
    kv("Date", rpt.report_date)
    kv("Location", rpt.site_location)
    kv("Prepared By", rpt.prepared_by)
    kv("Weather", rpt.weather)

    # Structured sections → table
    for title, rows in [
        ("Personnel on Site", rpt.personnel_on_site),
        ("Work Progress",     rpt.work_progress),
        ("Equipment",         rpt.equipment),
        ("Materials",         rpt.materials),
    ]:
        if rows:
            ui.label(title).classes("dpr-title")
            _row_table(rows)

    # Free-text sections → bullets
    for title, items in [
        ("HSE Observations", rpt.hse_observations),
        ("Quality Checks",   rpt.quality_checks),
        ("Issues & Risks",   rpt.issues_risks),
        ("Next Day Plan",    rpt.next_day_plan),
    ]:
        if items:
            ui.label(title).classes("dpr-title")
            _bullet_list(items)

    if rpt.incidents:
        ui.label("Incidents").classes("dpr-title")
        ui.label(rpt.incidents).classes("text-white")

    if rpt.source_files:
        ui.label("Source Files").classes("dpr-title")
        for f in rpt.source_files:
            ui.label(f"• {f}").classes("text-white")
