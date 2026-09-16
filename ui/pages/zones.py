"""Zone Progress Board — color-coded heatmap of construction stages per zone.

Auto-populates zones from the current report's work progress rows. Each zone
has an independent stage, updated via dropdown, persisted to session storage.
"""
from __future__ import annotations

from nicegui import ui

from ui import state
from ui.shell import page_shell


STAGES: list[tuple[str, str, str]] = [
    ("not_started",   "Not Started",   "#4f4f56"),
    ("excavation",    "Excavation",    "#8a6d3b"),
    ("blinding",      "Blinding",      "#4a80c4"),
    ("reinforcement", "Reinforcement", "#8a8a8a"),
    ("formwork",      "Formwork",      "#c47a3b"),
    ("pouring",       "Pouring",       "#22c55e"),
    ("curing",        "Curing",        "#8a4ab0"),
    ("complete",      "Complete",      "#0a6b2b"),
]

_STAGE_COLOR = {k: c for k, _, c in STAGES}
_STAGE_LABEL = {k: l for k, l, _ in STAGES}


def _zone_color(stage: str) -> str:
    return _STAGE_COLOR.get(stage, "#4f4f56")


def _zone_label(stage: str) -> str:
    return _STAGE_LABEL.get(stage, stage.replace("_", " ").title())


def _extract_zones_from_report(report) -> list[str]:
    """Zones from the report's work_progress, falling back to B<building>-F<floor>."""
    ids: set[str] = set()
    for r in report.work_progress:
        z = (r.get("zone") or "").strip()
        if z:
            ids.add(z)
            continue
        b = (r.get("building") or "").strip()
        f = (r.get("floor") or "").strip()
        if b:
            ids.add(f"B{b}" + (f"-F{f}" if f else ""))
    return sorted(ids)


def render():
    rpt = state.report()

    with page_shell(
        active="zones",
        title="Zone Progress Board",
        subtitle=(
            "Color-coded heatmap of construction stage per zone. "
            "Update each zone's stage with the dropdown — changes persist "
            "for this session and export with the report."
        ),
    ):
        if rpt is None:
            with ui.card().classes("dpr-card w-full"):
                ui.label("No report in this session.").classes("dpr-title text-xl")
                ui.label(
                    "Aggregate at least one file first — zones are derived "
                    "from the report's work progress rows."
                ).classes("text-white")
            with ui.row().classes("gap-3 mt-2"):
                ui.button("Back to Upload",
                          on_click=lambda: ui.navigate.to("/"))
            return

        zone_ids = _extract_zones_from_report(rpt)
        state.ensure_zones(zone_ids)

        if not zone_ids:
            ui.html(
                '<div class="dpr-zone-empty">'
                'No zones detected. Ensure your source reports include a '
                '"zone" field or a building + floor combination.'
                '</div>'
            )
            return

        # ── Legend ────────────────────────────────────────────────────
        legend_items = "".join(
            f'<span class="dpr-zone-legend-item">'
            f'  <span class="dpr-zone-legend-swatch" '
            f'        style="background:{color};"></span>'
            f'  {label}'
            f'</span>'
            for _, label, color in STAGES
        )
        ui.html(f'<div class="dpr-zone-legend">{legend_items}</div>')

        # ── Summary bar ───────────────────────────────────────────────
        def _render_summary() -> str:
            counts = {k: 0 for k, _, _ in STAGES}
            for z in state.zones().values():
                counts[z.get("stage", "not_started")] = \
                    counts.get(z.get("stage", "not_started"), 0) + 1
            cells = ""
            for key, label, color in STAGES:
                c = counts.get(key, 0)
                if c == 0:
                    continue
                cells += (
                    f'<div class="dpr-zone-summary-cell">'
                    f'  <div class="dpr-zone-summary-label" '
                    f'       style="color:{color};">{label}</div>'
                    f'  <div class="dpr-zone-summary-value">{c}</div>'
                    f'</div>'
                )
            return f'<div class="dpr-zone-summary">{cells}</div>'

        summary_html = ui.html(_render_summary()).classes("w-full")

        # ── Grid ──────────────────────────────────────────────────────
        @ui.refreshable
        def zone_grid():
            z = state.zones()
            with ui.element("div").classes("dpr-zone-grid"):
                for zid in zone_ids:
                    entry = z.get(zid, {"stage": "not_started"})
                    stage = entry.get("stage", "not_started")
                    color = _zone_color(stage)
                    label = _zone_label(stage)
                    updated = entry.get("updated", "") or "—"
                    note = entry.get("note", "")

                    with ui.element("div").classes("dpr-zone-card").style(
                        f"border-left-color: {color};"
                    ):
                        ui.html(
                            f'<div class="dpr-zone-id">{zid}</div>'
                            f'<div class="dpr-zone-stage-badge" '
                            f'     style="background:{color}22;'
                            f'            border-color:{color};'
                            f'            color:{color};">'
                            f'  {label}'
                            f'</div>'
                        )
                        ui.select(
                            {k: l for k, l, _ in STAGES},
                            value=stage,
                            on_change=lambda e, zz=zid: _on_stage_change(zz, e.value),
                        ).props("dense outlined").classes("w-full").style(
                            "font-size: 11px;"
                        )
                        ui.html(
                            f'<div class="dpr-zone-meta">'
                            f'Updated: {updated}'
                            + (f'<br/>{note}' if note else '')
                            + '</div>'
                        )

        def _on_stage_change(zone_id: str, stage: str) -> None:
            state.set_zone_stage(zone_id, stage)
            state.log(f"[zone] {zone_id} → {stage}")
            summary_html.content = _render_summary()
            zone_grid.refresh()

        zone_grid()

        # ── Footer actions ────────────────────────────────────────────
        def _reset_all() -> None:
            for zid in zone_ids:
                state.set_zone_stage(zid, "not_started")
            summary_html.content = _render_summary()
            zone_grid.refresh()
            ui.notify("All zones reset", color="orange")

        with ui.row().classes("gap-3 mt-4 items-center"):
            ui.button("Reset All Zones", on_click=_reset_all)
            ui.button("Back to Dashboard",
                      on_click=lambda: ui.navigate.to("/results"))
