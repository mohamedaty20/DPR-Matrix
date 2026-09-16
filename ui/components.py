"""Reusable widgets."""
from __future__ import annotations
from html import escape

from nicegui import ui

from ui import state
from ui.conflicts import conflict_banner, notes_banner


def section_title(text: str, subtitle: str = "") -> None:
    ui.label(text).classes("text-2xl font-bold dpr-title mt-4")
    if subtitle:
        ui.html(escape(subtitle)).classes("dpr-section-subtitle")


def log_console() -> ui.html:
    html = ui.html("").classes("dpr-console w-full")
    def refresh():
        html.content = "<br>".join(state.logs()[-80:]) or "— awaiting input —"
    ui.timer(1.0, refresh)
    refresh()
    return html


def _render_table(rows: list[dict]) -> None:
    if not rows:
        return
    keys: list[str] = []
    for r in rows:
        for k in r.keys():
            if k not in keys:
                keys.append(k)
    head = "".join(
        f'<th style="color:#00FF66;font-weight:700;padding:8px 10px;'
        f'text-align:left;background:#001a0a;'
        f'border-bottom:2px solid #00FF66;white-space:nowrap;">'
        f'{escape(k.replace("_", " ").title())}</th>' for k in keys
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
                f'{escape(str(v))}</td>'
            )
        body += f'<tr style="background:#0a0a0a;">{cells}</tr>'
    ui.html(
        '<div style="overflow-x:auto;background:#0a0a0a;'
        'border:1px solid #00FF66;border-radius:4px;margin-top:6px;">'
        '<table style="width:100%;border-collapse:collapse;background:#0a0a0a;">'
        f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
    ).classes("w-full")


def _bullets(items: list) -> None:
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
    kv("Shift", rpt.shift)

    for title, rows in [
        ("Work Progress", rpt.work_progress),
        ("Equipment",     rpt.equipment),
        ("Materials",     rpt.materials),
        ("Personnel",     rpt.personnel),
    ]:
        if rows:
            ui.label(title).classes("dpr-title")
            _render_table(rows)

    for title, items in [
        ("HSE Observations", rpt.hse_observations),
        ("Quality Checks",   rpt.quality_checks),
        ("Issues & Risks",   rpt.issues_risks),
        ("Next Day Plan",    rpt.next_day_plan),
    ]:
        if items:
            ui.label(title).classes("dpr-title")
            _bullets(items)

    if rpt.incidents:
        ui.label("Incidents").classes("dpr-title")
        ui.label(rpt.incidents).classes("text-white")

    if rpt.source_files:
        ui.label("Source Files").classes("dpr-title")
        for f in rpt.source_files:
            ui.label(f"• {f}").classes("text-white")


# ═══════════════════════════════════════════════════════════════════════════
# Pass 7.5 — Dashboard widgets
# ═══════════════════════════════════════════════════════════════════════════

def metadata_strip(items: list[tuple[str, str]]) -> None:
    """Horizontal key/value strip. items = [(label, value), ...]"""
    cells = "".join(
        f'<div class="dpr-meta-item">'
        f'  <div class="dpr-meta-label">{escape(str(k))}</div>'
        f'  <div class="dpr-meta-value">{escape(str(v) or "—")}</div>'
        f'</div>'
        for k, v in items
    )
    ui.html(f'<div class="dpr-meta-strip">{cells}</div>').classes("w-full")


def kpi_row(items: list[dict]) -> None:
    """
    items: list of {"label": str, "value": str|int, "sub": str, "tone": str}
    tone ∈ {"", "primary", "warning", "danger"}
    """
    cards = ""
    for it in items:
        tone = f" dpr-kpi-{it['tone']}" if it.get("tone") else ""
        sub = (
            f'<div class="dpr-kpi-sub">{escape(str(it["sub"]))}</div>'
            if it.get("sub") else ""
        )
        cards += (
            f'<div class="dpr-kpi{tone}">'
            f'  <div class="dpr-kpi-label">{escape(str(it["label"]))}</div>'
            f'  <div class="dpr-kpi-value">{escape(str(it["value"]))}</div>'
            f'  {sub}'
            f'</div>'
        )
    ui.html(f'<div class="dpr-kpi-grid">{cards}</div>').classes("w-full")


def bar_chart(
    title: str,
    items: list[tuple[str, float | int]],
    *,
    subtitle: str = "",
    unit: str = "",
    show_percent: bool = True,
    total_label: str = "Total",
) -> None:
    """
    Horizontal bar chart.
      items       = [(label, value), ...]  any length
      subtitle    = plain-English explanation rendered under the title
      unit        = optional suffix on the value (e.g. "pcs")
      show_percent= if True, appends "(NN%)" next to each value
      total_label = text before the big total in the header
    """
    if not items:
        return

    total = sum(float(v) for _, v in items)
    max_val = max((float(v) for _, v in items), default=0) or 1

    rows = ""
    for label, value in items:
        v = float(value)
        pct = (v / max_val) * 100.0
        pct_of_total = (v / total * 100.0) if total else 0.0

        value_html = f"{int(v) if v.is_integer() else v:g}{escape(unit)}"
        if show_percent and total > 0:
            value_html += f'<span class="dpr-bar-pct">{pct_of_total:.0f}%</span>'

        rows += (
            f'<div class="dpr-bar-row">'
            f'  <span class="dpr-bar-label">{escape(str(label))}</span>'
            f'  <div class="dpr-bar-track">'
            f'    <div class="dpr-bar-fill" style="width:{pct:.1f}%"></div>'
            f'  </div>'
            f'  <span class="dpr-bar-value">{value_html}</span>'
            f'</div>'
        )

    subtitle_html = (
        f'<div class="dpr-chart-subtitle">{escape(subtitle)}</div>'
        if subtitle else ""
    )
    total_html = (
        f'<div class="dpr-chart-total">'
        f'  {int(total) if float(total).is_integer() else f"{total:g}"}'
        f'  <span class="dpr-chart-total-label">{escape(total_label)}</span>'
        f'</div>'
    )

    ui.html(
        f'<div class="dpr-chart">'
        f'  <div class="dpr-chart-header">'
        f'    <div class="dpr-chart-title">{escape(title)}</div>'
        f'    {total_html}'
        f'  </div>'
        f'  {subtitle_html}'
        f'  <div class="dpr-bar-chart">{rows}</div>'
        f'</div>'
    ).classes("w-full")


def empty_chart(title: str, message: str) -> None:
    """Render an empty chart panel with a human-readable message."""
    ui.html(
        f'<div class="dpr-chart">'
        f'  <div class="dpr-chart-header">'
        f'    <div class="dpr-chart-title">{escape(title)}</div>'
        f'  </div>'
        f'  <div class="dpr-chart-empty">{escape(message)}</div>'
        f'</div>'
    ).classes("w-full")
