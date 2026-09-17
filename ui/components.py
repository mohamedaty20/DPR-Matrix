"""Reusable widgets — sections, tables, bars, histograms, matrices.

Pass 2 changes:
  - matrix_view (item 23): each column header shows the activity name
    with "working floors" on a second line beneath it; row heads show
    "B{building}" instead of "Bldg {building}".
  - ratio_bars legend: "Helpers" → "Assistants" (item 20).
  - new crew_rectangles component for the redesigned Crew Composition
    panel (item 22).
"""
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


_HIDDEN_COLUMNS = {"provenance", "sources"}
_NUMERIC_KEYS = {
    "quantity", "skilled", "helpers", "crew_total",
    "progress_pct", "count",
}
_CONFIDENCE_COLOR = {
    "high":   "#F2740C",   # orange
    "medium": "#ffb020",   # amber
    "low":    "#ff4d6a",   # red
}


def _cell_html(key: str, value) -> str:
    if isinstance(value, list):
        value = ", ".join(str(x) for x in value)

    if key == "confidence":
        v = str(value or "").strip().lower()
        color = _CONFIDENCE_COLOR.get(v, "#4f4f56")
        label = v.upper() if v else "—"
        return (
            f'<span style="display:inline-flex;align-items:center;gap:4px;">'
            f'<span style="width:5px;height:5px;border-radius:50%;'
            f'background:{color};display:inline-block;flex:0 0 auto;"></span>'
            f'<span style="color:{color};font-weight:600;font-size:10px;">'
            f'{escape(label)}</span></span>'
        )

    s = str(value or "").strip()
    if not s:
        return '<span style="color:#3a3a42;">—</span>'

    if key == "progress_pct":
        return f'{escape(s)}<span style="color:#85858c;">%</span>'

    return escape(s)


def _render_table(rows: list[dict]) -> None:
    if not rows:
        return

    keys: list[str] = []
    for r in rows:
        for k in r.keys():
            if k in _HIDDEN_COLUMNS:
                continue
            if k not in keys:
                keys.append(k)

    head = "".join(
        f'<th style="'
        f'color:#F2740C;font-weight:600;font-size:9.5px;'
        f'letter-spacing:0.05em;text-transform:uppercase;'
        f'padding:4px 6px;'
        f'text-align:{"right" if k in _NUMERIC_KEYS else "left"};'
        f'background:#2a1206;'
        f'border-bottom:1px solid #F2740C;'
        f'white-space:nowrap;">'
        f'{escape(k.replace("_", " "))}</th>'
        for k in keys
    )

    body = ""
    for i, r in enumerate(rows):
        bg = "#0a0a0a" if i % 2 == 0 else "#0b0d0e"
        cells = ""
        for k in keys:
            align = "right" if k in _NUMERIC_KEYS else "left"
            cells += (
                f'<td style="'
                f'color:#e8e8ea;font-size:10.5px;line-height:1.15;'
                f'padding:3px 6px;'
                f'text-align:{align};'
                f'border-bottom:1px solid rgba(242,116,12,0.06);'
                f'vertical-align:middle;white-space:nowrap;">'
                f'{_cell_html(k, r.get(k, ""))}</td>'
            )
        body += f'<tr style="background:{bg};">{cells}</tr>'

    ui.html(
        '<div style="overflow-x:auto;background:#0a0a0a;'
        'border:1px solid rgba(242,116,12,0.18);border-radius:8px;'
        'margin-top:6px;">'
        '<table style="border-collapse:collapse;background:#0a0a0a;width:100%;">'
        f'<thead><tr>{head}</tr></thead>'
        f'<tbody>{body}</tbody>'
        '</table></div>'
    ).classes("w-full")


def _bullets(items: list) -> None:
    for it in items:
        if isinstance(it, dict):
            text = " · ".join(f"{k}: {v}" for k, v in it.items()
                              if v and k != "sources")
            ui.label(f"• {text}").classes("text-white").style("font-size:12px;")
        else:
            ui.label(f"• {it}").classes("text-white").style("font-size:12px;")


def report_preview() -> None:
    rpt = state.report()
    if rpt is None:
        ui.label("No report generated yet.").classes("text-white")
        return

    conflict_banner(rpt.conflicts)
    notes_banner(rpt.notes)

    for title, rows in [
        ("Work Progress", rpt.work_progress),
        ("Equipment",     rpt.equipment),
        ("Materials",     rpt.materials),
        ("Personnel",     rpt.personnel),
    ]:
        if rows:
            ui.label(title).classes("dpr-title").style("margin-top:14px;")
            _render_table(rows)

    for title, items in [
        ("HSE Observations", rpt.hse_observations),
        ("Quality Checks",   rpt.quality_checks),
        ("Issues & Risks",   rpt.issues_risks),
        ("Next Day Plan",    rpt.next_day_plan),
    ]:
        if items:
            ui.label(title).classes("dpr-title").style("margin-top:14px;")
            _bullets(items)

    if rpt.incidents:
        ui.label("Incidents").classes("dpr-title").style("margin-top:14px;")
        ui.label(rpt.incidents).classes("text-white").style("font-size:12px;")


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


class _PanelCtx:
    def __init__(self, cls, title, subtitle, total, total_label):
        self.cls = cls
        self.title = title
        self.subtitle = subtitle
        self.total = total
        self.total_label = total_label
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


def panel(title: str, *, subtitle: str = "", total: str = "",
          total_label: str = "", wide: bool = False, empty: str = ""):
    cls = "dpr-panel dpr-panel-wide" if wide else "dpr-panel"
    return _PanelCtx(cls, title, subtitle, total, total_label)


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
    """Skilled vs assistants ratio bars. `helpers` percentage is the second
    tuple value — kept for data-shape compatibility, relabeled to assistants
    on the surface (item 20)."""
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
        '     style="background:rgba(242,116,12,0.28)"></span>Assistants</span>'
        '</div>'
    )
    ui.html(rows + legend).classes("w-full")


def histogram(buckets: list[tuple[str, int]]) -> None:
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
    """Building × Activity matrix (item 23).

    Each column header shows the activity name on line 1 and the fixed
    phrase "working floors" on line 2 (smaller, dimmer). Row heads are
    "B{n}" instead of "Bldg {n}".
    """
    acts = data["activities"]
    bldgs = data["buildings"]
    mat = data["matrix"]
    mx = data["max"] or 1
    if not acts or not bldgs:
        return

    grid_style = (
        f"grid-template-columns: 40px repeat({len(acts)}, minmax(64px, 1fr));"
    )
    html = f'<div class="dpr-matrix" style="{grid_style}">'

    # Empty corner cell + activity headers
    html += '<div class="dpr-matrix-head"></div>'
    for a in acts:
        html += (
            f'<div class="dpr-matrix-head dpr-matrix-head-2line">'
            f'  <span class="dpr-matrix-head-name">{escape(a)}</span>'
            f'  <span class="dpr-matrix-head-sub">working floors</span>'
            f'</div>'
        )

    # Rows
    for b in bldgs:
        html += f'<div class="dpr-matrix-row-head">B{escape(b)}</div>'
        for a in acts:
            v = mat.get(b, {}).get(a, 0)
            if v == 0:
                html += ('<div class="dpr-matrix-cell" '
                         'style="background:rgba(255,255,255,0.02);'
                         'color:#4f4f56;">·</div>')
            else:
                intensity = min(0.10 + (v / mx) * 0.55, 0.75)
                html += (f'<div class="dpr-matrix-cell" '
                         f'style="background:rgba(242,116,12,{intensity:.2f});">'
                         f'{v}</div>')
    html += "</div>"
    ui.html(html).classes("w-full")


def crew_rectangles(buildings: list[dict],
                    *, on_click=None, limit: int = 20) -> None:
    """Crew Composition — top N buildings by assistant count (item 22).

    Each building becomes its own small card showing building number,
    skilled crew, assistant crew, and total. If on_click is provided, each
    card becomes clickable and calls on_click(building_dict).

    `buildings` is SUM.compute(rpt)["buildings"] — sorted by crew desc; we
    re-sort by assistant count for this panel.
    """
    top = sorted(
        [b for b in buildings if b.get("assistants", 0) > 0],
        key=lambda x: (-x.get("assistants", 0), x.get("building", "")),
    )[:limit]

    if not top:
        ui.html('<div class="dpr-panel-empty">'
                'No assistant headcounts found.</div>')
        return

    cards = ""
    for b in top:
        bldg = escape(str(b.get("building", "—")))
        sk = int(b.get("skilled", 0) or 0)
        hp = int(b.get("assistants", 0) or 0)
        crew = int(b.get("crew", 0) or 0)
        cards += (
            f'<div class="dpr-crew-card" data-bldg="{bldg}">'
            f'  <div class="dpr-crew-card-title">Building {bldg}</div>'
            f'  <div class="dpr-crew-card-row">'
            f'    <span class="dpr-crew-card-key">Crew</span>'
            f'    <span class="dpr-crew-card-val">{sk}</span>'
            f'  </div>'
            f'  <div class="dpr-crew-card-row">'
            f'    <span class="dpr-crew-card-key">Assistant</span>'
            f'    <span class="dpr-crew-card-val">{hp}</span>'
            f'  </div>'
            f'  <div class="dpr-crew-card-row dpr-crew-card-total">'
            f'    <span class="dpr-crew-card-key">Total</span>'
            f'    <span class="dpr-crew-card-val">{crew}</span>'
            f'  </div>'
            f'</div>'
        )

    container = ui.html(f'<div class="dpr-crew-grid">{cards}</div>') \
        .classes("w-full")

    if on_click is not None:
        # Attach a JS-side click handler that emits an event to Python with
        # the building id. Uses the NiceGUI event system on the container.
        container.on("click", _make_crew_click_handler(on_click, top))


def _make_crew_click_handler(on_click, buildings):
    """Return a Python handler that reads the clicked card's data-bldg."""
    by_name = {str(b.get("building", "—")): b for b in buildings}

    def handler(e):
        # NiceGUI passes the raw DOM event; we read the closest card.
        try:
            target = (e.args or {}).get("target", {}) if isinstance(e.args, dict) else {}
        except Exception:
            target = {}
        # The simplest robust path — walk from the event path if provided.
        bldg = None
        try:
            path = e.args.get("path") if isinstance(e.args, dict) else None
            if path:
                for el in path:
                    ds = (el.get("dataset") or {}) if isinstance(el, dict) else {}
                    if "bldg" in ds:
                        bldg = ds["bldg"]
                        break
        except Exception:
            pass
        if bldg is None:
            return
        b = by_name.get(str(bldg))
        if b:
            on_click(b)

    return handler


def top_list(items: list[tuple[str, str | int]], *, start: int = 1) -> None:
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


def line_chart(
    title: str,
    series: list[dict],
    *,
    subtitle: str = "",
    x_labels: list[str] | None = None,
    height: int = 220,
) -> None:
    if not series or not series[0].get("points"):
        ui.html('<div class="dpr-panel-empty">No data to chart.</div>')
        return

    n = len(series[0]["points"])
    all_vals = [v for s in series for v in s["points"] if v is not None]
    if not all_vals:
        ui.html('<div class="dpr-panel-empty">No data to chart.</div>')
        return

    y_max = max(all_vals) or 1
    W, H = 900, height
    pad_l, pad_r, pad_t, pad_b = 52, 20, 18, 40
    inner_w = W - pad_l - pad_r
    inner_h = H - pad_t - pad_b

    def x_coord(i: int) -> float:
        return pad_l + ((i / (n - 1)) * inner_w if n > 1 else inner_w / 2)

    def y_coord(v: float) -> float:
        return pad_t + inner_h - (v / y_max) * inner_h

    grid = ""
    for i in range(5):
        y = pad_t + (i / 4) * inner_h
        val = y_max * (1 - i / 4)
        grid += (
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{pad_l + inner_w}" y2="{y:.1f}" '
            f'stroke="rgba(242,116,12,0.10)" stroke-width="1"/>'
            f'<text x="{pad_l - 8}" y="{y + 3:.1f}" text-anchor="end" '
            f'fill="#85858c" font-size="9.5" font-family="monospace">'
            f'{int(val) if val == int(val) else f"{val:.1f}"}</text>'
        )

    x_axis = ""
    if x_labels:
        step = max(1, len(x_labels) // 10)
        for i in range(0, len(x_labels), step):
            x = x_coord(i)
            x_axis += (
                f'<text x="{x:.1f}" y="{pad_t + inner_h + 16}" '
                f'text-anchor="middle" fill="#85858c" font-size="9.5" '
                f'font-family="monospace">{escape(str(x_labels[i]))}</text>'
            )

    paths = ""
    legend = ""
    for s in series:
        pts = s.get("points", [])
        color = s.get("color", "#F2740C")
        d_cmd = ""
        for i, v in enumerate(pts):
            if v is None:
                continue
            x, y = x_coord(i), y_coord(v)
            d_cmd += ("M" if d_cmd == "" else " L") + f"{x:.1f},{y:.1f}"
        if d_cmd:
            paths += (
                f'<path d="{d_cmd}" fill="none" stroke="{color}" '
                f'stroke-width="1.8" stroke-linejoin="round" '
                f'stroke-linecap="round"/>'
            )
        for i, v in enumerate(pts):
            if v is None:
                continue
            x, y = x_coord(i), y_coord(v)
            paths += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.4" fill="{color}"/>'
        legend += (
            f'<span style="display:inline-flex;align-items:center;gap:6px;'
            f'color:#85858c;font-size:10.5px;margin-right:12px;">'
            f'<span style="width:12px;height:2px;background:{color};'
            f'display:inline-block;"></span>{escape(s.get("name",""))}</span>'
        )

    sub_html = (
        f'<div class="dpr-panel-sub">{escape(subtitle)}</div>'
        if subtitle else ""
    )

    ui.html(
        f'<div class="dpr-panel" style="grid-column: 1 / -1;">'
        f'  <div class="dpr-panel-header">'
        f'    <div class="dpr-panel-title">{escape(title)}</div>'
        f'  </div>'
        f'  {sub_html}'
        f'  <div style="margin-bottom:8px;">{legend}</div>'
        f'  <svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet" '
        f'       style="width:100%;height:{H}px;display:block;">'
        f'    {grid}{x_axis}{paths}'
        f'  </svg>'
        f'</div>'
    ).classes("w-full")


_SEV_COLOR = {"high": "#ff4d6a", "medium": "#ffb020", "low": "#F2740C"}


def risk_forecast(data: dict) -> None:
    """Kept for compatibility — no longer called from the results page
    (item 14 removed the AI Risk menu). The function stays here so other
    callers don't break."""
    if not data:
        ui.html('<div class="dpr-panel-empty">No risk analysis yet.</div>')
        return

    overall = data.get("overall_risk", "insufficient_data")
    summary = data.get("summary", "")
    risks = data.get("risks", [])
    bottlenecks = data.get("bottlenecks", [])

    overall_color = _SEV_COLOR.get(overall, "#85858c")
    if overall == "insufficient_data":
        overall_color = "#85858c"

    header = (
        f'<div class="dpr-panel-header">'
        f'  <div class="dpr-panel-title">Risk &amp; Bottleneck Forecast</div>'
        f'  <div class="dpr-panel-total" style="color:{overall_color} !important;">'
        f'    {escape(overall.upper().replace("_", " "))}'
        f'  </div>'
        f'</div>'
    )

    summary_html = ""
    if summary:
        summary_html = (
            f'<div style="color:#e8e8ea;font-size:12px;line-height:1.5;'
            f'margin:4px 0 12px 0;padding:8px 11px;'
            f'background:rgba(242,116,12,0.04);'
            f'border-left:2px solid {overall_color};'
            f'border-radius:0 6px 6px 0;">'
            f'{escape(summary)}</div>'
        )

    risks_html = ""
    for r in risks:
        sev = r.get("severity", "low")
        color = _SEV_COLOR.get(sev, "#85858c")
        cat = escape(r.get("category", "").upper())
        title = escape(r.get("title", ""))
        detail = escape(r.get("detail", ""))
        evidence = escape(r.get("evidence", ""))
        reco = escape(r.get("recommendation", ""))
        risks_html += (
            f'<div style="border:1px solid rgba(242,116,12,0.12);'
            f'border-left:3px solid {color};'
            f'border-radius:8px;padding:10px 12px;margin-bottom:8px;'
            f'background:rgba(255,255,255,0.015);">'
            f'  <div style="display:flex;align-items:center;gap:8px;'
            f'      margin-bottom:5px;flex-wrap:wrap;">'
            f'    <span style="background:{color}22;color:{color};'
            f'        border:1px solid {color};padding:1px 6px;'
            f'        border-radius:999px;font-size:9px;font-weight:700;'
            f'        letter-spacing:0.08em;">{cat}</span>'
            f'    <span style="color:#e8e8ea;font-size:12.5px;font-weight:600;">'
            f'      {title}</span>'
            f'    <span style="color:#4f4f56;font-size:9.5px;'
            f'        margin-left:auto;font-weight:600;text-transform:uppercase;'
            f'        letter-spacing:0.08em;">{escape(sev)}</span>'
            f'  </div>'
            f'  <div style="color:#c8c8cc;font-size:11px;line-height:1.5;'
            f'      margin-bottom:6px;">{detail}</div>'
            + (f'<div style="color:#85858c;font-size:10.5px;line-height:1.45;'
               f'      margin-bottom:5px;">'
               f'<strong style="color:#4f4f56;">Evidence:</strong> {evidence}</div>'
               if evidence else "")
            + (f'<div style="color:#e8c19a;font-size:11px;line-height:1.45;'
               f'      padding:6px 9px;background:rgba(242,116,12,0.06);'
               f'      border-radius:6px;">'
               f'<strong style="color:#F2740C;">→</strong> {reco}</div>'
               if reco else "")
            + '</div>'
        )

    bottleneck_html = ""
    if bottlenecks:
        items = ""
        for b in bottlenecks:
            items += (
                f'<div class="dpr-toplist-row">'
                f'  <span class="dpr-toplist-rank">•</span>'
                f'  <span class="dpr-toplist-name">'
                f'    B{escape(str(b.get("building","")))} · '
                f'    {escape(str(b.get("activity","")))}</span>'
                f'  <span style="color:#ffb020;font-size:11px;">'
                f'    {escape(b.get("reason",""))}</span>'
                f'</div>'
            )
        bottleneck_html = (
            f'<div style="margin-top:12px;">'
            f'  <div style="color:#85858c;font-size:10px;letter-spacing:0.12em;'
            f'      text-transform:uppercase;font-weight:600;margin-bottom:6px;">'
            f'    Bottleneck Zones</div>'
            f'  <div class="dpr-toplist">{items}</div>'
            f'</div>'
        )

    if not risks and not bottlenecks and overall != "insufficient_data":
        risks_html = (
            '<div class="dpr-panel-empty">'
            'No risks flagged in the last 7 days.</div>'
        )

    ui.html(
        f'<div class="dpr-panel dpr-panel-wide">'
        f'  {header}'
        f'  {summary_html}'
        f'  {risks_html}'
        f'  {bottleneck_html}'
        f'</div>'
    ).classes("w-full")
