"""Render conflict warnings and note banners."""
from __future__ import annotations

from nicegui import ui


def conflict_banner(conflicts: list[dict]) -> None:
    if not conflicts:
        return

    hard = [c for c in conflicts if c.get("severity") == "hard"]
    soft = [c for c in conflicts if c.get("severity") != "hard"]

    if hard:
        with ui.card().classes("w-full").style(
            "background:#1a0d00 !important; border-color:#ff4d6a !important;"
        ):
            ui.label(
                f"⚠  {len(hard)} hard conflict(s) — review before export"
            ).style("color:#ff4d6a !important; font-weight:700;")

            for c in hard:
                field = c.get("field", "?").replace("_", " ").title()
                ctype = c.get("type", "value")
                resolved = c.get("resolution", "")
                reason = c.get("reason", "")

                with ui.element("div").style(
                    "padding:8px 0; border-top:1px solid rgba(255,77,106,0.18);"
                ):
                    ui.label(f"• {field}  [{ctype}]").style(
                        "color:#e8e8ea !important; font-weight:600; font-size:12.5px;"
                    )
                    for v in c.get("values", []):
                        ui.label(f"     {v}").style(
                            "color:#85858c !important; font-size:11.5px;"
                        )
                    if resolved:
                        ui.label(f"     → resolved: {resolved}").style(
                            "color:#ffb020 !important; font-size:11.5px;"
                        )
                    if reason:
                        ui.label(f"     {reason}").style(
                            "color:#4f4f56 !important; font-size:11px; font-style:italic;"
                        )

    if soft:
        with ui.card().classes("w-full").style(
            "background:#0d0d12 !important; border-color:rgba(34,197,94,0.25) !important;"
        ):
            ui.label(
                f"ℹ  {len(soft)} soft conflict(s) — auto-resolved within tolerance"
            ).style("color:#22c55e !important; font-weight:600; font-size:12px;")

            for c in soft:
                field = c.get("field", "?").replace("_", " ").title()
                resolved = c.get("resolution", "")
                ui.label(f"• {field}  →  {resolved}").style(
                    "color:#85858c !important; font-size:11.5px; padding-left:8px;"
                )


def notes_banner(notes: list[str]) -> None:
    if not notes:
        return
    with ui.card().classes("w-full").style(
        "background:#0a1f12 !important; border-color:#22c55e !important;"
    ):
        for n in notes:
            ui.label(f"ℹ {n}").classes("text-white").style("font-size:12px;")
