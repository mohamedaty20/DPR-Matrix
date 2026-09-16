"""SaaS shell — pure CSS grid layout.

Deliberately does NOT use ui.header() or ui.left_drawer(). Those rely on
Quasar's JS drawer system, which has client-behavior branches and can
render inconsistently depending on viewport detection. This version is
just two <div> columns — no runtime layout logic, no fixed positioning,
nothing that can silently fail.
"""
from __future__ import annotations

from contextlib import contextmanager
from html import escape

from nicegui import ui

from ui import state


_NAV = [
    ("home",    "Upload",  "cloud_upload", "/"),
    ("results", "Report",  "analytics",    "/results"),
    ("history", "History", "history",      "/history"),
]


@contextmanager
def page_shell(*, active: str, title: str, subtitle: str = ""):
    with ui.element("div").classes("dpr-shell"):
        # ── Sidebar column ────────────────────────────────────────────
        with ui.element("aside").classes("dpr-shell-sidebar"):
            with ui.element("div").classes("dpr-shell-brand"):
                ui.html(
                    '<span class="dpr-brand-mark">DPR</span>'
                    '<span class="dpr-brand-name"> Matrix</span>'
                )

            with ui.element("nav").classes("dpr-shell-nav"):
                for key, label, icon, href in _NAV:
                    cls = "dpr-nav-item"
                    if key == active:
                        cls += " dpr-nav-active"
                    with ui.link(target=href).classes(cls):
                        with ui.row().classes("items-center gap-3 no-wrap"):
                            ui.icon(icon).classes("dpr-nav-icon")
                            ui.label(label).classes("dpr-nav-label")

            ui.element("div").classes("dpr-shell-sidebar-spacer")

            with ui.element("div").classes("dpr-shell-sidebar-footer"):
                q = len(state.queue_files())
                if q:
                    ui.html(f'<span class="dpr-pill">{q} queued</span>')

                rpt = state.report()
                if rpt is not None:
                    ui.html(
                        f'<span class="dpr-pill">'
                        f'<span class="dpr-pill-dot"></span>'
                        f'{len(rpt.work_progress)} rows</span>'
                    )
                    if rpt.conflicts:
                        ui.html(
                            f'<span class="dpr-pill dpr-pill-warn">'
                            f'{len(rpt.conflicts)} conflicts</span>'
                        )

        # ── Main column ───────────────────────────────────────────────
        with ui.element("main").classes("dpr-shell-main"):
            with ui.element("header").classes("dpr-shell-topbar"):
                with ui.element("div").classes("dpr-shell-topbar-left"):
                    ui.html(
                        f'<span class="dpr-topbar-crumb">'
                        f'{escape(str(title))}</span>'
                    )
                with ui.element("div").classes("dpr-shell-topbar-right"):
                    if state.report_id():
                        ui.html(
                            f'<span class="dpr-pill">'
                            f'<span class="dpr-pill-dot"></span>'
                            f'Report #{state.report_id()}</span>'
                        )

            with ui.element("div").classes("dpr-page-header"):
                ui.label(title).classes("dpr-page-title")
                if subtitle:
                    ui.label(subtitle).classes("dpr-page-subtitle")

            with ui.element("div").classes("dpr-page-body"):
                yield
