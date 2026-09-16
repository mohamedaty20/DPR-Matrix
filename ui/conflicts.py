"""Render conflict warnings and note banners."""
from nicegui import ui


def conflict_banner(conflicts: list[dict]) -> None:
    if not conflicts:
        return
    with ui.card().classes("w-full").style(
        "background:#1a0d00 !important; border-color:#FFB300 !important;"
    ):
        ui.label(f"⚠ {len(conflicts)} conflict(s) across source reports") \
            .style("color:#FFB300 !important; font-weight:700;")
        for c in conflicts:
            field = c.get("field", "?").replace("_", " ").title()
            vals = c.get("values", [])
            ui.label(f"• {field}: " + " | ".join(str(v) for v in vals)) \
                .classes("text-white").style("font-size:12px;")


def notes_banner(notes: list[str]) -> None:
    if not notes:
        return
    with ui.card().classes("w-full").style(
        "background:#0a1f12 !important; border-color:#22c55e !important;"
    ):
        for n in notes:
            ui.label(f"ℹ {n}").classes("text-white").style("font-size:12px;")
