"""Site Map — interactive matplotlib scatter with search + zoom."""
from __future__ import annotations

import base64
from collections import Counter

from nicegui import ui

from core.normalize import to_float
from core.scatter_map import render_scatter, STAGE_COLORS, STAGE_LABELS
from ui import state
from ui.shell import page_shell


# ═══════════════════════════════════════════════════════════════════════════
# Stage inference
# ═══════════════════════════════════════════════════════════════════════════
_ORDER = {
    "not_started":   0,
    "excavation":    1,
    "blinding":      2,
    "reinforcement": 3,
    "formwork":      4,
    "pouring":       5,
    "curing":        6,
    "finishing":     7,
    "complete":      8,
}
_LABEL = STAGE_LABELS
_COLOR = STAGE_COLORS

_ACTIVITY_TO_STAGE = {
    "excavation":     "excavation",
    "backfilling":    "excavation",
    "blinding":       "blinding",
    "steel fixing":   "reinforcement",
    "reinforcement":  "reinforcement",
    "formwork":       "formwork",
    "concrete works": "pouring",
    "concreting":     "pouring",
    "curing":         "curing",
    "waterproofing":  "finishing",
    "mortar works":   "finishing",
    "brickworks":     "finishing",
    "plastering":     "finishing",
    "sealer works":   "finishing",
    "painting":       "finishing",
    "tiling":         "finishing",
    "gypsum works":   "finishing",
    "ceiling works":  "finishing",
    "carpentry":      "finishing",
    "electrical":     "finishing",
    "plumbing":       "finishing",
}


def _stage_for_activity(activity: str) -> str | None:
    a = (activity or "").lower().strip()
    if not a:
        return None
    if a in _ACTIVITY_TO_STAGE:
        return _ACTIVITY_TO_STAGE[a]
    for k, v in _ACTIVITY_TO_STAGE.items():
        if k in a:
            return v
    return None


def _floor_sort(s: str):
    try:
        return (0, int(s))
    except (ValueError, TypeError):
        return (1, s)


def _infer_stage(activities: dict, prog_sum: float, prog_n: int) -> str:
    advanced = -1
    for a in activities:
        st = _stage_for_activity(a)
        if st:
            advanced = max(advanced, _ORDER[st])
    if advanced >= 0:
        for k, v in _ORDER.items():
            if v == advanced:
                return k
    if prog_n == 0:
        return "not_started"
    avg = prog_sum / prog_n
    if avg >= 95: return "complete"
    if avg >= 70: return "finishing"
    if avg >= 40: return "pouring"
    if avg > 0:   return "excavation"
    return "not_started"


def _derive_zones(rpt) -> list[dict]:
    groups: dict[str, dict] = {}
    for r in rpt.work_progress:
        b = (r.get("building") or "").strip()
        z = (r.get("zone") or "").strip()
        key = z or (f"B{b}" if b else "N/A")

        g = groups.setdefault(key, {
            "id": key, "label": b or z or "N/A",
            "building": b, "floors": set(), "rows": 0,
            "activities": {}, "crew": 0, "low_conf": 0,
            "prog_sum": 0.0, "prog_n": 0,
        })
        fl = (r.get("floor") or "").strip()
        if fl:
            g["floors"].add(fl)
        g["rows"] += 1
        a = (r.get("activity") or "").strip()
        if a:
            g["activities"][a] = g["activities"].get(a, 0) + 1
        g["crew"] += int(to_float(r.get("skilled")) or 0) \
                     + int(to_float(r.get("helpers")) or 0)
        if r.get("confidence") == "low":
            g["low_conf"] += 1
        p = to_float(r.get("progress_pct"))
        if p is not None:
            g["prog_sum"] += p
            g["prog_n"] += 1

    out = []
    for key, g in groups.items():
        stage = _infer_stage(g["activities"], g["prog_sum"], g["prog_n"])
        avg = (g["prog_sum"] / g["prog_n"]) if g["prog_n"] else None
        top = ""
        if g["activities"]:
            top = max(g["activities"].items(), key=lambda kv: kv[1])[0]
        out.append({
            "id": key, "label": g["label"], "building": g["building"],
            "floors": sorted(g["floors"], key=_floor_sort),
            "rows": g["rows"], "activities": g["activities"],
            "top_activity": top, "crew": g["crew"], "stage": stage,
            "avg_progress": avg, "low_conf": g["low_conf"],
        })
    out.sort(
        key=lambda x: (
            int(x["building"]) if x["building"].isdigit() else 10**9,
        )
    )
    return out


# ═══════════════════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════════════════
_ZONES_CSS = """
<style>
/* ── Search + zoom bar ─────────────────────────────────────────── */
.dpr-map-toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.dpr-search-wrap {
  flex: 1;
  min-width: 220px;
  position: relative;
}
.dpr-search-status {
  font-size: 11px;
  color: #85858c;
  padding: 4px 2px 0 2px;
  min-height: 16px;
}
.dpr-search-status b { color: #F2740C; }
.dpr-search-status.err { color: #ff4d6a; }
.dpr-zoom-group {
  display: inline-flex;
  background: #0c0c0f;
  border: 1px solid rgba(242,116,12,0.28);
  border-radius: 8px;
  overflow: hidden;
}
.dpr-zoom-btn {
  background: transparent;
  border: none;
  color: #85858c;
  font-family: inherit;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 6px 12px;
  cursor: pointer;
  border-right: 1px solid rgba(242,116,12,0.15);
}
.dpr-zoom-btn:last-child { border-right: none; }
.dpr-zoom-btn:hover { color: #F2740C; background: rgba(242,116,12,0.06); }
.dpr-zoom-btn.active {
  background: rgba(242,116,12,0.14);
  color: #F2740C;
}

/* ── Scroll container ──────────────────────────────────────────── */
.dpr-map-scroll {
  width: 100%;
  max-height: 72vh;
  overflow: auto;
  border: 1px solid rgba(242,116,12,0.28);
  border-radius: 12px;
  background: #08080a;
  -webkit-overflow-scrolling: touch;
}
.dpr-map-scale {
  position: relative;
  width: 100%;
  transition: width .15s ease;
}
.dpr-scatter-img {
  width: 100%;
  height: auto;
  display: block;
  pointer-events: none;
  user-select: none;
  -webkit-user-drag: none;
}

/* ── Hotspots ──────────────────────────────────────────────────── */
.dpr-hotspot {
  position: absolute;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  cursor: pointer;
  background: transparent;
  border: 2px solid transparent;
  z-index: 4;
  transition: background-color .12s ease, border-color .12s ease;
  -webkit-tap-highlight-color: transparent;
}
.dpr-hotspot:hover {
  background: rgba(242,116,12,0.10);
  border-color: rgba(242,116,12,0.5);
}
.dpr-hotspot.selected {
  background: rgba(242,116,12,0.16);
  border-color: #F2740C;
  box-shadow: 0 0 0 2px rgba(242,116,12,0.32),
              0 0 24px rgba(242,116,12,0.55);
  animation: dpr-hs-pulse 1.8s ease-in-out infinite;
}
@keyframes dpr-hs-pulse {
  0%, 100% { box-shadow: 0 0 0 2px rgba(242,116,12,0.32),
                        0 0 24px rgba(242,116,12,0.55); }
  50%      { box-shadow: 0 0 0 2px rgba(242,116,12,0.32),
                        0 0 32px rgba(242,116,12,0.8); }
}

/* ── Detail panel ──────────────────────────────────────────────── */
.dpr-map-wrap {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 14px;
  margin-bottom: 16px;
  align-items: start;
}
@media (max-width: 960px) {
  .dpr-map-wrap { grid-template-columns: 1fr; }
}
.dpr-sel-panel {
  background: linear-gradient(180deg, #0c0c0f 0%, #08080a 100%);
  border: 1px solid rgba(242,116,12,0.28);
  border-radius: 12px;
  padding: 16px 18px;
  position: sticky;
  top: 68px;
  max-height: calc(100vh - 84px);
  overflow-y: auto;
}
@media (max-width: 960px) {
  .dpr-sel-panel { position: relative; top: 0; max-height: none; }
}
.dpr-sel-empty {
  color: #4f4f56;
  font-size: 12px;
  text-align: center;
  padding: 36px 12px;
  line-height: 1.6;
  font-style: italic;
}
.dpr-sel-band {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 7px 11px;
  border-radius: 8px;
  margin-bottom: 12px;
  color: #050506;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}
.dpr-sel-title {
  color: #e8e8ea;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.02em;
  margin-bottom: 2px;
}
.dpr-sel-sub {
  color: #85858c;
  font-size: 11px;
  margin-bottom: 14px;
}
.dpr-sel-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(242,116,12,0.08);
  font-size: 12px;
}
.dpr-sel-row:last-of-type { border-bottom: none; }
.dpr-sel-key { color: #85858c; }
.dpr-sel-val { color: #e8e8ea; font-weight: 700; text-align: right; }
.dpr-sel-val.orange { color: #F2740C; }
.dpr-sel-val.warn   { color: #ffb020; }
.dpr-sel-val.risk   { color: #ff4d6a; }
.dpr-sel-val.ok     { color: #0a8a3b; }
.dpr-sel-prog {
  height: 6px;
  background: rgba(255,255,255,0.05);
  border-radius: 999px;
  overflow: hidden;
  margin: 6px 0 4px 0;
}
.dpr-sel-prog-fill { height: 100%; border-radius: 999px; }
.dpr-sel-acts {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 8px;
}
.dpr-sel-act {
  font-size: 10px;
  color: #c8c8cc;
  background: rgba(242,116,12,0.07);
  border: 1px solid rgba(242,116,12,0.18);
  padding: 2px 7px;
  border-radius: 4px;
}

/* ── Bullet summary ────────────────────────────────────────────── */
.dpr-points {
  background: linear-gradient(180deg, #0c0c0f 0%, #08080a 100%);
  border: 1px solid rgba(242,116,12,0.20);
  border-radius: 12px;
  padding: 18px 20px;
}
.dpr-pts-section { margin-bottom: 16px; }
.dpr-pts-section:last-child { margin-bottom: 0; }
.dpr-pts-head {
  color: #F2740C;
  font-size: 10.5px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-weight: 700;
  margin-bottom: 8px;
  padding-bottom: 5px;
  border-bottom: 1px solid rgba(242,116,12,0.10);
}
.dpr-pts-list { list-style: none; margin: 0; padding: 0; }
.dpr-pts-list li {
  position: relative;
  padding: 5px 0 5px 18px;
  color: #c8c8cc;
  font-size: 12px;
  line-height: 1.55;
  border-bottom: 1px solid rgba(242,116,12,0.05);
}
.dpr-pts-list li:last-child { border-bottom: none; }
.dpr-pts-list li:before {
  content: "▸";
  position: absolute;
  left: 0; top: 5px;
  color: #F2740C;
  font-size: 11px;
  font-weight: 700;
}
.dpr-pts-list li.warn:before { color: #ffb020; content: "⚠"; }
.dpr-pts-list li.risk:before { color: #ff4d6a; content: "⚠"; }
.dpr-pts-list li.ok:before   { color: #0a8a3b; content: "✓"; }
.dpr-pts-list b { color: #e8e8ea; font-weight: 700; }
</style>
"""


# ═══════════════════════════════════════════════════════════════════════════
# Selected zone detail panel
# ═══════════════════════════════════════════════════════════════════════════
def _render_selected(z: dict | None) -> None:
    if z is None:
        ui.html(
            '<div class="dpr-sel-empty">'
            'Tap a point on the scatter map — or search a building — '
            'to see its status, crew, and activities.'
            '</div>'
        )
        return

    color = _COLOR.get(z["stage"], "#4f4f56")
    label = _LABEL.get(z["stage"], z["stage"])
    prog = z["avg_progress"]

    if prog is None:
        prog_html = (
            '<div style="color:#4f4f56;font-size:11px;padding:6px 0;">'
            'No progress data in source.</div>'
        )
    else:
        pct = max(0.0, min(100.0, prog))
        prog_html = (
            f'<div class="dpr-sel-prog">'
            f'  <div class="dpr-sel-prog-fill" '
            f'       style="width:{pct:.0f}%;background:{color};"></div>'
            f'</div>'
            f'<div style="color:#85858c;font-size:10.5px;">'
            f'  Avg progress · {pct:.0f}%</div>'
        )

    floors_txt = " · ".join(z["floors"]) if z["floors"] else "—"
    conf_cls = "risk" if z["low_conf"] else "ok"
    conf_val = (
        f'{z["low_conf"]} low-conf row(s)' if z["low_conf"] else "clean"
    )
    acts_html = "".join(
        f'<span class="dpr-sel-act">{a}</span>'
        for a in sorted(z["activities"].keys())
    )

    ui.html(
        f'<div class="dpr-sel-band" style="background:{color};">'
        f'  <span>{label}</span>'
        f'  <span>{z["crew"]} crew</span>'
        f'</div>'
        f'<div class="dpr-sel-title">Building {z["building"] or z["id"]}</div>'
        f'<div class="dpr-sel-sub">Zone identifier: {z["id"]}</div>'
        f'<div class="dpr-sel-row">'
        f'  <span class="dpr-sel-key">Crew on site</span>'
        f'  <span class="dpr-sel-val orange">{z["crew"]}</span>'
        f'</div>'
        f'<div class="dpr-sel-row">'
        f'  <span class="dpr-sel-key">Floors</span>'
        f'  <span class="dpr-sel-val">{len(z["floors"])} ({floors_txt})</span>'
        f'</div>'
        f'<div class="dpr-sel-row">'
        f'  <span class="dpr-sel-key">Work rows</span>'
        f'  <span class="dpr-sel-val">{z["rows"]}</span>'
        f'</div>'
        f'<div class="dpr-sel-row">'
        f'  <span class="dpr-sel-key">Top activity</span>'
        f'  <span class="dpr-sel-val">{z["top_activity"] or "—"}</span>'
        f'</div>'
        f'<div class="dpr-sel-row">'
        f'  <span class="dpr-sel-key">Data confidence</span>'
        f'  <span class="dpr-sel-val {conf_cls}">{conf_val}</span>'
        f'</div>'
        f'<div style="margin-top:12px;">{prog_html}</div>'
        f'<div style="color:#85858c;font-size:10.5px;'
        f'      letter-spacing:0.10em;text-transform:uppercase;'
        f'      font-weight:600;margin-top:14px;margin-bottom:2px;">'
        f'  Activities</div>'
        f'<div class="dpr-sel-acts">{acts_html}</div>'
    )


# ═══════════════════════════════════════════════════════════════════════════
# Bullet summary
# ═══════════════════════════════════════════════════════════════════════════
def _build_points(zones: list[dict], rpt) -> dict:
    total_crew = sum(z["crew"] for z in zones)
    total_rows = sum(z["rows"] for z in zones)
    total_acts = len({a for z in zones for a in z["activities"]})

    stage_counts = Counter(z["stage"] for z in zones)
    top_stage = stage_counts.most_common(1)[0] if stage_counts else ("not_started", 0)

    top_crew = sorted(
        [z for z in zones if z["crew"] > 0],
        key=lambda z: -z["crew"],
    )[:3]

    sorted_stage = sorted(zones, key=lambda z: _ORDER.get(z["stage"], 0))
    latest = sorted_stage[-1] if sorted_stage else None
    earliest = sorted_stage[0] if sorted_stage else None

    stalled = [
        z for z in zones
        if z["stage"] in ("not_started", "excavation") and z["crew"] > 0
    ]
    high_crew_low = [
        z for z in zones
        if z["crew"] >= 10
        and z["avg_progress"] is not None
        and z["avg_progress"] < 40
    ]
    low_conf = [z for z in zones if z["low_conf"] > 0]
    n_hard = sum(1 for c in rpt.conflicts if c.get("severity") == "hard")

    overview = [
        f"<b>{len(zones)}</b> active zone(s) · <b>{total_crew}</b> total crew · "
        f"<b>{total_rows}</b> work rows · <b>{total_acts}</b> activities",
        f"Site predominantly at <b>{_LABEL[top_stage[0]]}</b> "
        f"({top_stage[1]} of {len(zones)} zones)",
    ]
    if top_crew:
        overview.append(
            "Highest crew: " + " · ".join(
                f"<b>{z['id']}</b> ({z['crew']})" for z in top_crew
            )
        )

    watch: list[tuple[str, str]] = []
    if stalled:
        watch.append((
            "warn",
            f"<b>{len(stalled)}</b> zone(s) at excavation with crew assigned "
            f"— possible stall: {', '.join(z['id'] for z in stalled)}",
        ))
    if high_crew_low:
        top = high_crew_low[0]
        watch.append((
            "warn",
            f"<b>{top['id']}</b> has {top['crew']} crew but only "
            f"{top['avg_progress']:.0f}% progress — resources may be idle",
        ))
    if low_conf:
        watch.append((
            "warn",
            f"<b>{len(low_conf)}</b> zone(s) contain low-confidence rows — "
            f"verify before sign-off: {', '.join(z['id'] for z in low_conf[:5])}",
        ))
    if n_hard:
        watch.append((
            "risk",
            f"<b>{n_hard}</b> hard conflict(s) across source files — "
            f"see Conflicts banner on Report dashboard",
        ))
    if not watch:
        watch.append((
            "ok",
            "No material issues detected — data is consistent across sources",
        ))

    actions: list[str] = []
    if stalled:
        actions.append(
            f"Reallocate crew to accelerate "
            f"{', '.join(z['id'] for z in stalled[:3])} or confirm the delay"
        )
    if high_crew_low:
        actions.append(
            f"Audit productivity in <b>{high_crew_low[0]['id']}</b> — "
            f"{high_crew_low[0]['crew']} crew at "
            f"{high_crew_low[0]['avg_progress']:.0f}%"
        )
    if low_conf:
        actions.append(
            "Open Reconcile Sources and verify flagged zones before export"
        )
    if latest and _ORDER[latest["stage"]] >= _ORDER["pouring"]:
        actions.append(
            f"Schedule cube tests / curing verification for "
            f"<b>{latest['id']}</b> per compliance practice"
        )
    if earliest and latest and earliest["id"] != latest["id"]:
        gap = _ORDER[latest["stage"]] - _ORDER[earliest["stage"]]
        if gap >= 4:
            actions.append(
                f"Site progression gap between <b>{earliest['id']}</b> "
                f"({_LABEL[earliest['stage']]}) and <b>{latest['id']}</b> "
                f"({_LABEL[latest['stage']]}) — review sequencing"
            )
    if not actions:
        actions.append("Continue as planned — no corrective action required today")

    return {"overview": overview, "watch": watch, "actions": actions}


# ═══════════════════════════════════════════════════════════════════════════
# Render
# ═══════════════════════════════════════════════════════════════════════════
def render():
    with page_shell(
        active="zones",
        title="Site Map",
        subtitle=(
            "Interactive scatter of every active building. Zoom, search, "
            "and tap a point to inspect it."
        ),
    ):
        ui.add_head_html(_ZONES_CSS, shared=False)

        rpt = state.report()
        if rpt is None:
            with ui.card().classes("dpr-card w-full"):
                ui.label("No report in this session.").classes("dpr-title text-xl")
                ui.label(
                    "Aggregate at least one file first — the map is "
                    "derived from the report's work progress rows."
                ).classes("text-white")
            with ui.row().classes("gap-3 mt-2"):
                ui.button("Back to Upload",
                          on_click=lambda: ui.navigate.to("/"))
            return

        zones = _derive_zones(rpt)
        if not zones:
            ui.html(
                '<div style="background:#0c0c0f;'
                'border:1px dashed rgba(242,116,12,0.4);'
                'border-radius:12px;padding:40px;text-align:center;'
                'color:#85858c;font-size:13px;">'
                'No zones detected in this report.</div>'
            )
            return

        W_PX = 1600.0
        H_PX = 760.0

        ui_state = {
            "highlight_id": None,
            "zoom": 1.0,
            "search_q": "",
            "selection": None,
        }

        # ═══════════════════════════════════════════════════════════
        # Toolbar — search + zoom
        # ═══════════════════════════════════════════════════════════
        with ui.element("div").classes("dpr-map-toolbar"):
            with ui.element("div").classes("dpr-search-wrap"):
                search_input = ui.input(
                    placeholder="Search building (e.g. 78 or B78)",
                ).props("dense outlined clearable").classes("w-full")

            with ui.element("div").classes("dpr-zoom-group"):
                zoom_btns = {}
                for label, val in [("1×", 1.0), ("2×", 2.0),
                                    ("3×", 3.0), ("4×", 4.0)]:
                    b = ui.element("button").classes("dpr-zoom-btn")
                    if val == 1.0:
                        b.classes(add="active")
                    with b:
                        ui.html(label)
                    b.on("click", lambda v=val, el=b: _set_zoom(v, el))
                    zoom_btns[val] = b

        search_status = ui.html("").classes("dpr-search-status")

        # ═══════════════════════════════════════════════════════════
        # Map container
        # ═══════════════════════════════════════════════════════════
        with ui.element("div").classes("dpr-map-wrap"):
            with ui.element("div").classes("dpr-map-scroll"):
                scale_wrap = ui.element("div").classes("dpr-map-scale")

                @ui.refreshable
                def map_view():
                    hl = ui_state["highlight_id"]
                    png_bytes, hotspots = render_scatter(
                        zones, highlight_id=hl,
                    )
                    b64 = base64.b64encode(png_bytes).decode("ascii")

                    scale_wrap.clear()
                    with scale_wrap:
                        ui.html(
                            f'<img class="dpr-scatter-img" '
                            f'src="data:image/png;base64,{b64}" '
                            f'alt="Site map"/>'
                        )
                        for hs in hotspots:
                            x_pct = hs["x_px"] / W_PX * 100.0
                            y_pct = hs["y_px"] / H_PX * 100.0
                            z = hs["zone"]
                            is_sel = (
                                ui_state["selection"] is not None
                                and ui_state["selection"]["id"] == z["id"]
                            )
                            cls = "dpr-hotspot" + (" selected" if is_sel else "")
                            el = ui.element("div").classes(cls)
                            el.style(f"left: {x_pct:.3f}%; top: {y_pct:.3f}%;")
                            el.on("click", lambda zz=z: _pick(zz))

            # ── Detail panel ────────────────────────────────────────
            with ui.element("div").classes("dpr-sel-panel"):
                @ui.refreshable
                def detail_panel():
                    _render_selected(ui_state["selection"])
                detail_panel()

        # ═══════════════════════════════════════════════════════════
        # Callbacks
        # ═══════════════════════════════════════════════════════════
        def _pick(z: dict):
            ui_state["selection"] = z
            ui_state["highlight_id"] = z["id"]
            map_view.refresh()
            detail_panel.refresh()

        def _set_zoom(val: float, active_btn):
            ui_state["zoom"] = val
            scale_wrap.style(f"width: {int(val * 100)}%;")
            for v, b in zoom_btns.items():
                if v == val:
                    b.classes(add="active")
                else:
                    b.classes(remove="active")

        def _on_search(e):
            q = (e.value or "").strip().lower()
            if q == ui_state["search_q"]:
                return
            ui_state["search_q"] = q

            if not q:
                ui_state["highlight_id"] = None
                search_status.content = ""
                map_view.refresh()
                return

            # Match order: exact building number, exact id, prefix
            match: dict | None = None
            for z in zones:
                b = str(z.get("building", "")).lower()
                i = str(z.get("id", "")).lower()
                if q == b or q == i:
                    match = z
                    break
            if match is None:
                for z in zones:
                    b = str(z.get("building", "")).lower()
                    i = str(z.get("id", "")).lower()
                    if b.startswith(q) or i.startswith(q):
                        match = z
                        break

            if match is None:
                ui_state["highlight_id"] = None
                search_status.content = (
                    f'<span class="err">No building matches "{q}"</span>'
                )
                map_view.refresh()
                return

            ui_state["highlight_id"] = match["id"]
            ui_state["selection"] = match
            search_status.content = (
                f'Highlighting <b>Building {match["building"] or match["id"]}</b>'
            )
            map_view.refresh()
            detail_panel.refresh()

        search_input.on("update:model-value", _on_search)

        # ═══════════════════════════════════════════════════════════
        # Initial render
        # ═══════════════════════════════════════════════════════════
        map_view()

        # ═══════════════════════════════════════════════════════════
        # Bullet summary
        # ═══════════════════════════════════════════════════════════
        pts = _build_points(zones, rpt)

        overview_html = "".join(f"<li>{b}</li>" for b in pts["overview"])
        watch_html = "".join(
            f'<li class="{cls}">{b}</li>' for cls, b in pts["watch"]
        )
        actions_html = "".join(f"<li>{b}</li>" for b in pts["actions"])

        ui.html(
            f'<div class="dpr-points">'
            f'  <div class="dpr-pts-section">'
            f'    <div class="dpr-pts-head">Site at a glance</div>'
            f'    <ul class="dpr-pts-list">{overview_html}</ul>'
            f'  </div>'
            f'  <div class="dpr-pts-section">'
            f'    <div class="dpr-pts-head">Watch list</div>'
            f'    <ul class="dpr-pts-list">{watch_html}</ul>'
            f'  </div>'
            f'  <div class="dpr-pts-section">'
            f'    <div class="dpr-pts-head">Recommended actions</div>'
            f'    <ul class="dpr-pts-list">{actions_html}</ul>'
            f'  </div>'
            f'</div>'
        )

        with ui.row().classes("gap-2 mt-3 flex-wrap"):
            ui.button("Back to Dashboard",
                      on_click=lambda: ui.navigate.to("/results"))
            ui.button("Reconcile Sources",
                      on_click=lambda: ui.navigate.to("/reconcile"))
