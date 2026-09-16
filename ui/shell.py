"""SaaS shell — persistent sidebar + top bar wrapped around every page."""
from __future__ import annotations

from contextlib import contextmanager

from nicegui import ui

from ui import state


_NAV = [
    ("home",    "Upload",       "cloud_upload",  "/"),
    ("results", "Report",       "analytics",     "/results"),
    ("history", "History",      "history",       "/history"),
]


@contextmanager
def page_shell(*, active: str, title: str, subtitle: str = ""):
    # ── Top bar ───────────────────────────────────────────────────────
    with ui.header().classes("dpr-topbar"):
        with ui.row().classes("items-center gap-3 no-wrap"):
            ui.html(
                '<span class="dpr-brand-mark">DPR</span>'
                '<span class="dpr-brand-name">Matrix</span>'
            )
        ui.element("div").classes("dpr-topbar-spacer")
        with ui.row().classes("items-center gap-3 no-wrap"):
            q = len(state.queue_files())
            if q:
                ui.html(
                    f'<span class="dpr-pill">{q} queued</span>'
                )
            if state.report_id():
                ui.html(
                    f'<span class="dpr-pill">'
                    f'<span class="dpr-pill-dot"></span>'
                    f'Report #{state.report_id()}</span>'
                )
            elif state.report():
                ui.html(
                    f'<span class="dpr-pill">'
                    f'<span class="dpr-pill-dot"></span>'
                    f'Live session</span>'
                )

    # ── Sidebar ───────────────────────────────────────────────────────
    with ui.left_drawer(value=True, bordered=False).classes("dpr-sidebar"):
        with ui.column().classes("w-full gap-1"):
            for key, label, icon, href in _NAV:
                cls = "dpr-nav-item"
                if key == active:
                    cls += " dpr-nav-active"
                with ui.link(target=href).classes(cls):
                    with ui.row().classes("items-center gap-3 no-wrap"):
                        ui.icon(icon).classes("dpr-nav-icon")
                        ui.label(label).classes("dpr-nav-label")

        ui.element("div").classes("dpr-sidebar-gap")

        with ui.column().classes("w-full gap-2"):
            ui.label("SESSION").classes("dpr-sidebar-section")
            q = state.queue_files()
            ui.label(f"{len(q)} file(s) queued").classes("dpr-sidebar-stat")
            if state.report():
                n_rows = len(state.report().work_progress)
                n_conf = len(state.report().conflicts)
                ui.label(f"{n_rows} work rows").classes("dpr-sidebar-stat")
                ui.label(
                    f"{n_conf} conflict(s)"
                    + (" ✓" if n_conf == 0 else "")
                ).classes("dpr-sidebar-stat")

        ui.element("div").classes("dpr-sidebar-gap")
        with ui.column().classes("w-full gap-2"):
            ui.label("ACTIONS").classes("dpr-sidebar-section")
            with ui.link(target="/").classes("dpr-nav-item"):
                with ui.row().classes("items-center gap-3 no-wrap"):
                    ui.icon("add").classes("dpr-nav-icon")
                    ui.label("New Session").classes("dpr-nav-label")

    # ── Content ───────────────────────────────────────────────────────
    with ui.column().classes("dpr-content w-full"):
        with ui.column().classes("dpr-page-header w-full"):
            ui.label(title).classes("dpr-page-title")
            if subtitle:
                ui.label(subtitle).classes("dpr-page-subtitle")

        with ui.column().classes("dpr-page-body w-full"):
            yield
