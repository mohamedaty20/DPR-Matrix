"""Results — the report dashboard.

Layout:
  1. Header + metadata strip
  2. Download bar (prominent, top)
  3. KPI cards
  4. Charts (crew by building · work by activity)
  5. Conflict / notes banners
  6. Full report preview
  7. Footer: download bar (again) + navigation
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

from nicegui import ui

from core.normalize import to_float
from ui import state
from ui.components import (
    bar_chart,
    kpi_row,
    metadata_strip,
    report_preview,
    section_title,
)


# ── Filename stem ────────────────────────────────────────────────────────
def _safe(s: str, fallback: str = "report") -> str:
    s = (s or "").strip()
    s = re.sub(r"[^\w\-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or fallback


def _stem() -> str:
    rpt = state.report()
    if rpt is None:
        return "DPR_report"
    proj = _safe(rpt.project_name, "project")
    date = _safe(rpt.report_date, "") or "undated"
    return f"DPR_{proj}_{date}"


# ── Derived metrics ──────────────────────────────────────────────────────
def _total_crew(report) -> int:
    total = 0
    for r in report.work_progress:
        total += int(to_float(r.get("skilled")) or 0)
        total += int(to_float(r.get("helpers")) or 0)
    return total


def _crew_by_building(report) -> list[tuple[str, int]]:
    acc: dict[str, int] = defaultdict(int)
    for r in report.work_progress:
        b = (r.get("building") or "—").strip() or "—"
        sk = to_float(r.get("skilled")) or 0
        hp = to_float(r.get("helpers")) or 0
        acc[b] += int(sk + hp)

    def sort_key(kv):
        try:
            return (0, int(kv[0]))
        except (ValueError, TypeError):
            return (1, kv[0])
    return sorted(acc.items(), key=sort_key)


def _work_by_activity(report) -> list[tuple[str, int]]:
    c: Counter = Counter()
    for r in report.work_progress:
        a = (r.get("activity") or "").strip()
        if a:
            c[a] += 1
    return c.most_common(10)


# ── Download handlers ────────────────────────────────────────────────────
def _download_pdf():
    try:
        from core.exporters.pdf_exporter import export_pdf
        data = export_pdf(state.report())
        ui.download(data, f"{_stem()}.pdf")
    except Exception as e:
        import traceback
        traceback.print_exc()
        state.log(f"[err] PDF export: {type(e).__name__}: {e}")
        ui.notify(f"PDF export failed: {e}", color="red")


def _download_excel():
    try:
        from core.exporters.excel_exporter import export_excel
        data = export_excel(state.report())
        ui.download(data, f"{_stem()}.xlsx")
    except Exception as e:
        import traceback
        traceback.print_exc()
        state.log(f"[err] Excel export: {type(e).__name__}: {e}")
        ui.notify(f"Excel export failed: {e}", color="red")


def _download_txt():
    try:
        from core.exporters.txt_exporter import export_txt
        data = export_txt(state.report()).encode("utf-8")
        ui.download(data, f"{_stem()}.txt")
    except Exception as e:
        import traceback
        traceback.print_exc()
        state.log(f"[err] TXT export: {type(e).__name__}: {e}")
        ui.notify(f"TXT export failed: {e}", color="red")


# ── Reusable download row ────────────────────────────────────────────────
def _download_row(*, prominent: bool = False) -> None:
    with ui.element("div").classes("dpr-download-bar"):
        with ui.element("div").classes("dpr-download-bar-label"):
            ui.html(
                "Export this report"
                f"<small>{_stem()}.pdf · .xlsx · .txt</small>"
            )
        with ui.row().classes("gap-2 items-center"):
            pdf_btn = ui.button("Download PDF", on_click=_download_pdf)
            if prominent:
                pdf_btn.classes("dpr-btn-primary")
            ui.button("Download Excel", on_click=_download_excel)
            ui.button("Download TXT",   on_click=_download_txt)


# ── Empty state ──────────────────────────────────────────────────────────
def _empty_state() -> None:
    n_queue = len(state.queue_files())
    with ui.card().classes("dpr-card w-full"):
        ui.label("No report in this session.").classes("dpr-title text-xl")
        if n_queue == 0:
            ui.label(
                "No files were uploaded. Go back, add at least one "
                "PDF / XLSX / PNG / JPG / TXT, then click Aggregate."
            ).classes("text-white")
        else:
            ui.label(
                f"{n_queue} file(s) are queued but no report was produced. "
                "The job may have been cancelled or failed — check the "
                "Activity Log on the upload page."
            ).classes("text-white")

    if state.logs():
        section_title("Last activity")
        with ui.card().classes("dpr-card w-full"):
            ui.html("<br>".join(state.logs()[-15:])) \
                .classes("dpr-console w-full")

    with ui.row().classes("gap-3 mt-4"):
        ui.button("Back to Upload", on_click=lambda: ui.navigate.to("/"))
        ui.button("History", on_click=lambda: ui.navigate.to("/history"))


# ── Main render ──────────────────────────────────────────────────────────
def render():
    ui.label("Report Dashboard").classes("dpr-app-title")
    ui.label(
        "Merged Daily Progress Report — normalized across all source files, "
        "ready for engineer review and export."
    ).classes("dpr-app-subtitle")
    ui.separator()

    rpt = state.report()
    n_queue = len(state.queue_files())

    ui.label(
        f"Queue: {n_queue} file(s) · report: "
        f"{'ready' if rpt else 'none'} · log lines: {len(state.logs())}"
    ).classes("dpr-muted")

    if rpt is None:
        _empty_state()
        return

    # ── 1. Metadata strip ─────────────────────────────────────────────
    metadata_strip([
        ("Project",     rpt.project_name or "—"),
        ("Date",        rpt.report_date  or "—"),
        ("Location",    rpt.site_location or "—"),
        ("Prepared by", rpt.prepared_by  or "—"),
        ("Weather",     rpt.weather      or "—"),
        ("Shift",       rpt.shift        or "—"),
    ])

    # ── 2. Top download bar ───────────────────────────────────────────
    _download_row(prominent=True)

    # ── 3. KPI cards ──────────────────────────────────────────────────
    total_crew = _total_crew(rpt)
    buildings = {r.get("building") for r in rpt.work_progress if r.get("building")}
    activities = {r.get("activity") for r in rpt.work_progress if r.get("activity")}

    kpi_row([
        {
            "label": "Files Merged",
            "value": len(rpt.source_files),
            "sub":   ", ".join(rpt.source_files[:2]) +
                     (" …" if len(rpt.source_files) > 2 else ""),
            "tone":  "primary",
        },
        {
            "label": "Work Rows",
            "value": len(rpt.work_progress),
            "sub":   f"{len(buildings)} building(s) · {len(activities)} activity",
        },
        {
            "label": "Total Crew",
            "value": total_crew,
            "sub":   "skilled + helpers across all rows",
        },
        {
            "label": "Conflicts",
            "value": len(rpt.conflicts),
            "sub":   "source disagreements" if rpt.conflicts else "no disagreements",
            "tone":  "danger" if rpt.conflicts else "primary",
        },
    ])

    # ── 4. Charts ─────────────────────────────────────────────────────
    crew_items = _crew_by_building(rpt)[:8]
    activity_items = _work_by_activity(rpt)

    if crew_items or activity_items:
        with ui.element("div").classes("dpr-chart-grid"):
            if crew_items:
                bar_chart("Crew by building", crew_items)
            if activity_items:
                bar_chart("Work rows by activity", activity_items)

    # ── 5. Conflicts + notes ──────────────────────────────────────────
    from ui.conflicts import conflict_banner, notes_banner
    conflict_banner(rpt.conflicts)
    notes_banner(rpt.notes)

    # ── 6. Full preview ───────────────────────────────────────────────
    with ui.card().classes("dpr-card w-full"):
        section_title("Full Report")
        report_preview()

    # ── 7. Bottom download bar ────────────────────────────────────────
    _download_row()

    # ── 8. Footer ─────────────────────────────────────────────────────
    with ui.row().classes("gap-3 mt-4 items-center"):
        if state.report_id():
            ui.label(f"Saved as report #{state.report_id()}") \
                .classes("dpr-muted")
        ui.button("History", on_click=lambda: ui.navigate.to("/history"))
        ui.button("New Session", on_click=_new_session)


def _new_session():
    state.reset()
    state.clear_queue()
    state.clear_cancel()
    ui.navigate.to("/")
