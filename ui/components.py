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
    """Render a plain-HTML table — bypasses Quasar's white-on-white defaults."""
    if not rows:
        return
    from html import escape as _esc

    keys: list[str] = []
    for r in rows:
        for k in r.keys():
            if k not in keys:
                keys.append(k)

    head = "".join(
        f'<th style="color:#00FF66;font-weight:700;padding:8px 10px;'
        f'text-align:left;background:#001a0a;'
        f'border-bottom:2px solid #00FF66;white-space:nowrap;">'
        f'{_esc(k.replace("_", " ").title())}</th>'
        for k in keys
    )

    body = ""
    for r in rows:
        cells = ""
        for k in keys:
            v = r.get(k, "")
            if isinstance(v, list):
                v = ", ".join(str(x) for x in v)
            cells += (
                f'<td style="color:#ffffff;padding:6px 10px;'
                f'border-bottom:1px solid #1f3f1f;vertical-align:top;">'
                f'{_esc(str(v))}</td>'
            )
        body += f'<tr style="background:#0a0a0a;">{cells}</tr>'

    html = (
        '<div style="overflow-x:auto;background:#0a0a0a;'
        'border:1px solid #00FF66;border-radius:4px;margin-top:6px;">'
        '<table style="width:100%;border-collapse:collapse;background:#0a0a0a;">'
        f'<thead><tr>{head}</tr></thead>'
        f'<tbody>{body}</tbody>'
        '</table></div>'
    )
    ui.html(html).classes("w-full")


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
