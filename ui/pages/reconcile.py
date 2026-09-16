"""Reconcile Sources — side-by-side per-source view for every merged key."""
from __future__ import annotations

from html import escape

from nicegui import ui

from ui import state
from ui.shell import page_shell


_FIELDS = [
    ("skilled",      "Skilled"),
    ("helpers",      "Helpers"),
    ("quantity",     "Quantity"),
    ("unit",         "Unit"),
    ("progress_pct", "Progress %"),
    ("zone",         "Zone"),
    ("notes",        "Notes"),
]


def _entry_html(entry: dict) -> str:
    b = entry.get("building", "")
    f = entry.get("floor", "")
    a = entry.get("activity", "")
    sources = entry.get("sources", [])
    resolved = entry.get("resolved", {})
    by_src = entry.get("by_source", {})

    # Header
    header = (
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:baseline;gap:12px;flex-wrap:wrap;">'
        f'  <div style="font-size:13px;font-weight:600;color:#e8e8ea;">'
        f'    Building {escape(str(b))} · Floor {escape(str(f))} · '
        f'    {escape(str(a))}'
        f'  </div>'
        f'  <div style="color:#4f4f56;font-size:11px;">'
        f'    {len(sources)} source(s)'
        f'  </div>'
        f'</div>'
    )

    # Source columns
    headers_html = '<th style="color:#85858c;text-align:left;padding:6px 10px;font-size:10.5px;text-transform:uppercase;letter-spacing:0.08em;">Field</th>'
    for src in sources:
        headers_html += (
            f'<th style="color:#85858c;text-align:left;padding:6px 10px;'
            f'font-size:10.5px;text-transform:uppercase;'
            f'letter-spacing:0.08em;">{escape(src)}</th>'
        )
    headers_html += (
        '<th style="color:#22c55e;text-align:left;padding:6px 10px;'
        'font-size:10.5px;text-transform:uppercase;'
        'letter-spacing:0.08em;">Resolved</th>'
    )

    rows_html = ""
    for key, label in _FIELDS:
        # Skip fields where every source is blank
        any_val = any((by_src.get(s, {}).get(key) or "") for s in sources)
        resolved_val = str(resolved.get(key, "") or "")
        if not any_val and not resolved_val:
            continue

        cells = (
            f'<td style="padding:6px 10px;color:#85858c;font-size:11.5px;">'
            f'{label}</td>'
        )
        for src in sources:
            v = by_src.get(src, {}).get(key, "")
            v_str = escape(str(v or "—"))
            v_color = "#e8e8ea" if v else "#4f4f56"
            cells += (
                f'<td style="padding:6px 10px;color:{v_color};'
                f'font-size:11.5px;">{v_str}</td>'
            )
        r_color = "#22c55e" if resolved_val else "#4f4f56"
        cells += (
            f'<td style="padding:6px 10px;color:{r_color};'
            f'font-size:11.5px;font-weight:600;">'
            f'{escape(resolved_val or "—")}</td>'
        )
        rows_html += f"<tr>{cells}</tr>"

    table = (
        '<div style="overflow-x:auto;margin-top:12px;">'
        '<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr>{headers_html}</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        '</table></div>'
    )

    return (
        f'<div style="background:#0c0c0f;border:1px solid rgba(34,197,94,0.14);'
        f'border-radius:12px;padding:16px 18px;margin-bottom:12px;">'
        f'{header}{table}</div>'
    )


def render():
    rpt = state.report()
    with page_shell(
        active="results",
        title="Reconcile Sources",
        subtitle=(
            "Side-by-side comparison of every source file's values for each "
            "merged building/floor/activity key. The right-hand column shows "
            "the value the aggregator resolved to."
        ),
    ):
        if rpt is None:
            with ui.card().classes("dpr-card w-full"):
                ui.label("No report in this session.").classes("dpr-title text-xl")
                ui.label("Aggregate some files first, then come back.") \
                    .classes("text-white")
            with ui.row().classes("gap-3 mt-2"):
                ui.button("Back to Upload",
                          on_click=lambda: ui.navigate.to("/"))
            return

        entries = rpt.reconciliation or []

        with ui.row().classes("gap-2 items-center mt-1"):
            ui.button("← Back to Dashboard",
                      on_click=lambda: ui.navigate.to("/results"))
            ui.label(f"{len(entries)} merged key(s)").classes("dpr-muted")

        if not entries:
            with ui.card().classes("dpr-card w-full"):
                ui.label("No reconciliation data.").classes("text-white")
                ui.label(
                    "This report was produced before reconciliation "
                    "was enabled. Re-run aggregation to populate it."
                ).classes("dpr-muted")
            return

        for entry in entries:
            ui.html(_entry_html(entry)).classes("w-full")
