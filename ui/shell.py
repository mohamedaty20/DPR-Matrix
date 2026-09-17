"""SaaS shell — pure CSS grid layout.

Left sidebar: pre-created projects loaded from Turso (item 4).
Every page also gets the professional site footer (item 25).
"""
from __future__ import annotations

from contextlib import contextmanager
from html import escape

from nicegui import ui

from ui import state


# Utility links kept above the project list — "New upload" is the only
# always-present entry now that the old 4-item nav has been replaced.
_UTILITY = [
    ("home", "New upload", "add_circle", "/"),
]


def _fetch_projects() -> list[dict]:
    """One entry per unique project_name from Turso, latest first."""
    try:
        from core.db import list_reports
        rows = list_reports(limit=200)
    except Exception:
        return []

    seen: dict[str, dict] = {}
    for r in rows:
        name = (r.get("project_name") or "").strip()
        if not name:
            name = f"Report #{r['id']}"
        if name in seen:
            continue
        seen[name] = {
            "name": name,
            "report_id": int(r["id"]),
            "created_at": r.get("created_at") or "",
            "site": r.get("site_location") or "",
        }
    return list(seen.values())


def _load_project(report_id: int) -> None:
    try:
        from core.db import get_report
    except Exception:
        ui.notify("Could not reach the project database.",
                  color="red", position="top")
        return
    try:
        rpt = get_report(report_id)
    except Exception as ex:
        ui.notify(f"Could not load project: {ex}",
                  color="red", position="top")
        return
    if rpt is None:
        ui.notify("That project could not be found.",
                  color="red", position="top")
        return
    state.set_report(rpt)
    state.set_report_id(report_id)
    state.clear_events()
    ui.navigate.to("/results")


def _project_item(p: dict) -> None:
    def _open(_ev=None) -> None:
        _load_project(p["report_id"])

    date_txt = (p.get("created_at") or "")[:10]
    with ui.element("div").classes("dpr-nav-proj-item").on("click", _open):
        ui.html(
            f'<div class="dpr-nav-proj-name">{escape(p["name"])}</div>'
        )
        meta_bits = [b for b in (p.get("site") or "", date_txt) if b]
        if meta_bits:
            ui.html(
                f'<div class="dpr-nav-proj-meta">'
                f'{escape(" · ".join(meta_bits))}</div>'
            )


_FOOTER_HTML = """
<footer class="dpr-site-footer">
  <div class="dpr-site-footer-inner">
    <div class="dpr-site-footer-title">DPR-Matrix</div>
    <p class="dpr-site-footer-text">
      DPR-Matrix is a Daily Progress Reporting platform that turns site
      reports, spreadsheets, photographs, and PDFs into one unified,
      AI-extracted project dashboard &mdash; engineered for construction
      teams who need accurate numbers, fast.
    </p>
    <p class="dpr-site-footer-text dpr-site-footer-cta">
      Your feedback is valuable and helps make DPR-Matrix better every day.
    </p>
    <div class="dpr-site-footer-copy">
      &copy; 2025 Mohamed Abd Al Aty &mdash; Founder, DPR-Matrix.
      All rights reserved.
    </div>
  </div>
</footer>
"""


@contextmanager
def page_shell(*, active: str, title: str, subtitle: str = ""):
    projects = _fetch_projects()

    with ui.element("div").classes("dpr-shell"):
        with ui.element("aside").classes("dpr-shell-sidebar"):
            with ui.element("div").classes("dpr-shell-brand"):
                ui.html(
                    '<span class="dpr-brand-mark">DPR</span>'
                    '<span class="dpr-brand-name"> Matrix</span>'
                )

            with ui.element("nav").classes("dpr-shell-nav"):
                for key, label, icon, href in _UTILITY:
                    cls = "dpr-nav-item"
                    if key == active:
                        cls += " dpr-nav-active"
                    with ui.link(target=href).classes(cls):
                        with ui.row().classes("items-center gap-3 no-wrap"):
                            ui.icon(icon).classes("dpr-nav-icon")
                            ui.label(label).classes("dpr-nav-label")

            # ── Pre-created projects (Turso-backed) ────────────────
            ui.html('<div class="dpr-nav-section-label">Your projects</div>')

            if not projects:
                ui.html(
                    '<div class="dpr-nav-empty">'
                    'No saved projects yet.<br>'
                    'Upload site reports to create your first one.'
                    '</div>'
                )
            else:
                with ui.element("div").classes("dpr-nav-projects"):
                    for p in projects:
                        _project_item(p)

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

            ui.html(_FOOTER_HTML)
