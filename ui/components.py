"""Reusable widgets — sections, tables, bars, histograms, matrices."""
from __future__ import annotations
from html import escape

from nicegui import ui

from ui import state
from ui.conflicts import conflict_banner, notes_banner


# ── Section ──────────────────────────────────────────────────────────────
def section_title(text: str, subtitle: str = "") -> None:
    ui.label(text).classes("text-2xl font-bold dpr-title mt-4")
    if subtitle:
        ui.html(escape(subtitle)).classes("dpr-section-subtitle")


# ── Console ──────────────────────────────────────────────────────────────
def log_console() -> ui.html:
    html = ui.html("").classes("dpr-console w-full")
    def refresh():
        html.content = "<br>".join(state.logs()[-80:]) or "— awaiting input —"
    ui.timer(1.0, refresh)
    refresh()
    return html


# ── Table ────────────────────────────────────────────────────────────────
def _render_table(rows: list[dict]) -> None:
    if not rows:
        return
    keys: list[str] = []
    for r in rows:
        for k in r.keys():
            if k not in keys:
                keys.append(k)
    head = "".join(
        f'<th style="color:#22c55e;font-weight:700;padding:8px 10px;'
        f'text-align:left;background:#0a1f12;'
        f'border-bottom:2px solid #22c55e;white-space:nowrap;">'
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
                f'border-bottom:1px solid #1a2e22;vertical-align:top;">'
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
# Analytics widgets
# ═══════════════════════════════════════════════════════════════════════════

def metadata_strip(items: list[tuple[str, str]]) -> None:
    cells = "".join(
        f'<div class="dpr-meta-item">'
        f'  <div class="dpr-meta-label">{escape(str(k))}</div>'
        f'  <div class="dpr-meta-value">{escape(str(v) or "—")}</div>'
        f'</div>'
        for k, v in items
    )
    ui.html(f'<div class="dpr-meta-strip">{cells}</div>').classes("w-full")


def stat_grid(items: list[dict]) -> None:
    """items: [{"label","value","sub","tone"}], tone ∈ {"", primary, warning, danger}"""
    cards = ""
    for it in items:
        tone = f" dpr-stat-{it['tone']}" if it.get("tone") else ""
        sub = (
            f'<div class="dpr-stat-sub">{escape(str(it["sub"]))}</div>'
            if it.get("sub") else ""
        )
        cards += (
            f'<div class="dpr-stat{tone}">'
            f'  <div class="dpr-stat-label">{escape(str(it["label"]))}</div>'
            f'  <div class="dpr-stat-value">{escape(str(it["value"]))}</div>'
            f'  {sub}'
            f'</div>'
        )
    ui.html(f'<div class="dpr-stat-grid">{cards}</div>').classes("w-full")


def panel(
    title: str,
    *,
    subtitle: str = "",
    total: str = "",
    total_label: str = "",
    wide: bool = False,
    empty: str = "",
):
    """
    Context manager. Renders a chart panel; inside, call bar_list / ratio_bars /
    histogram / matrix / top_list to fill it.
    """
    cls = "dpr-panel dpr-panel-wide" if wide else "dpr-panel"
    return _PanelCtx(cls, title, subtitle, total, total_label, empty)


class _PanelCtx:
    def __init__(self, cls, title, subtitle, total, total_label, empty):
        self.cls = cls
        self.title = title
        self.subtitle = subtitle
        self.total = total
        self.total_label = total_label
        self.empty = empty
        self._cm = None

    def __enter__(self):
        self._cm = ui.element("div").classes(self.cls)
        self._cm.__enter__()
        total_html = (
            f'<div class="dpr-panel-total">'
            f'  {escape(str(self.total))}'
            f'  <small>{escape(self.total_label)}</small>'
            f'</div>'
            if self.total else ""
        )
        sub_html = (
            f'<div class="dpr-panel-sub">{escape(self.subtitle)}</div>'
            if self.subtitle else ""
        )
        ui.html(
            f'<div class="dpr-panel-header">'
            f'  <div class="dpr-panel-title">{escape(self.title)}</div>'
            f'  {total_html}'
            f'</div>'
            f'{sub_html}'
        )
        return self

    def __exit__(self, exc_type, exc, tb):
        return self._cm.__exit__(exc_type, exc, tb)

    def message(self, msg: str) -> None:
        ui.html(
            f'<div class="dpr-panel-empty">{escape(msg)}</div>'
        )


def bar_list(items: list[tuple[str, float | int]],
             *, unit: str = "", show_pct: bool = True) -> None:
    if not items:
        return
    total = sum(float(v) for _, v in items) or 1
    max_val = max((float(v) for _, v in items), default=0) or 1

    rows = ""
    for label, value in items:
        v = float(value)
        pct = v / max_val * 100
        pct_total = v / total * 100
        val_txt = f"{int(v) if v.is_integer() else v:g}{escape(unit)}"
        if show_pct:
            val_txt += f'<span class="dpr-bar-pct">{pct_total:.0f}%</span>'
        rows += (
            f'<div class="dpr-bar-row">'
            f'  <span class="dpr-bar-label">{escape(str(label))}</span>'
            f'  <div class="dpr-bar-track">'
            f'    <div class="dpr-bar-fill" style="width:{pct:.1f}%"></div>'
            f'  </div>'
            f'  <span class="dpr-bar-value">{val_txt}</span>'
            f'</div>'
        )
    ui.html(f'<div class="dpr-bars">{rows}</div>').classes("w-full")


def ratio_bars(items: list[tuple[str, float, float, float]]) -> None:
    """
    items: [(label, skilled_pct, helpers_pct, total), ...]
    Renders stacked skilled|helpers bar per row.
    """
    if not items:
        return
    rows = ""
    for label, sk_pct, hp_pct, total in items:
        total_i = int(total) if float(total).is_integer() else total
        rows += (
            f'<div class="dpr-ratio-row">'
            f'  <div class="dpr-ratio-top">'
            f'    <span class="dpr-ratio-label">{escape(str(label))}</span>'
            f'    <span class="dpr-ratio-total">{total_i} crew</span>'
            f'  </div>'
            f'  <div class="dpr-ratio-track">'
            f'    <div class="dpr-ratio-skilled" style="width:{sk_pct:.1f}%"></div>'
            f'    <div class="dpr-ratio-helpers" style="width:{hp_pct:.1f}%"></div>'
            f'  </div>'
            f'</div>'
        )
    legend = (
        '<div class="dpr-ratio-legend">'
        '  <span><span class="dpr-ratio-dot" '
        '     style="background:var(--dpr-primary)"></span>Skilled</span>'
        '  <span><span class="dpr-ratio-dot" '
        '     style="background:rgba(0,255,102,0.28)"></span>Helpers</span>'
        '</div>'
    )
    ui.html(rows + legend).classes("w-full")


def histogram(buckets: list[tuple[str, int]]) -> None:
    """buckets: [(label, count), ...]. Bar height = count/max."""
    if not buckets:
        return
    mx = max((c for _, c in buckets), default=0) or 1
    cols = ""
    for label, count in buckets:
        pct_h = (count / mx) * 100 if count else 0
        cols += (
            f'<div class="dpr-hist-col">'
            f'  <div class="dpr-hist-value">{count}</div>'
            f'  <div class="dpr-hist-bar-wrap">'
            f'    <div class="dpr-hist-bar" style="height:{pct_h:.1f}%"></div>'
            f'  </div>'
            f'  <div class="dpr-hist-label">{escape(label)}</div>'
            f'</div>'
        )
    ui.html(f'<div class="dpr-histogram">{cols}</div>').classes("w-full")


def matrix_view(data: dict) -> None:
    """
    data from analytics.activity_matrix():
      {"activities": [...], "buildings": [...], "matrix": {...}, "max": int}
    """
    acts = data["activities"]
    bldgs = data["buildings"]
    mat = data["matrix"]
    mx = data["max"] or 1

    if not acts or not bldgs:
        return

    # Header row: blank + activities
    n_cols = len(acts) + 1
    grid_style = f"grid-template-columns: 120px repeat({len(acts)}, minmax(56px, 1fr));"

    html = f'<div class="dpr-matrix" style="{grid_style}">'
    html += '<div class="dpr-matrix-head"></div>'
    for a in acts:
        html += f'<div class="dpr-matrix-head">{escape(a)}</div>'

    for b in bldgs:
        html += f'<div class="dpr-matrix-row-head">Building {escape(b)}</div>'
        for a in acts:
            v = mat.get(b, {}).get(a, 0)
            if v == 0:
                html += (
                    '<div class="dpr-matrix-cell" '
                    'style="background:rgba(255,255,255,0.02);color:#4f4f56;">'
                    '·</div>'
                )
            else:
                intensity = min(0.10 + (v / mx) * 0.55, 0.75)
                html += (
                    f'<div class="dpr-matrix-cell" '
                    f'style="background:rgba(0,255,102,{intensity:.2f});">'
                    f'{v}</div>'
                )
    html += "</div>"
    ui.html(html).classes("w-full")


def top_list(items: list[tuple[str, str | int]], *, start: int = 1) -> None:
    """items: [(name, value), ...]"""
    if not items:
        return
    rows = ""
    for i, (name, value) in enumerate(items, start=start):
        rows += (
            f'<div class="dpr-toplist-row">'
            f'  <span class="dpr-toplist-rank">{i:02d}</span>'
            f'  <span class="dpr-toplist-name">{escape(str(name))}</span>'
            f'  <span class="dpr-toplist-value">{escape(str(value))}</span>'
            f'</div>'
        )
    ui.html(f'<div class="dpr-toplist">{rows}</div>').classes("w-full")
