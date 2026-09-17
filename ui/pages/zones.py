"""Site Overview — interactive matplotlib pie chart with search + zoom.

Item 24 rebuild retained:
  - Search: 100 / B100 / bldg 100 / whitespace all resolve.
  - Scroll-wheel zoom (laptop) and pinch zoom (mobile).
  - Click a slice hotspot to select, click again to deselect.

Current pass: the matplotlib scatter was replaced with a pie chart
(slice size = crew, slice colour = stage). Same search, same detail
panel, same hotspot interaction.
"""
from __future__ import annotations

import base64
import re
import time
from collections import Counter

from nicegui import ui

from core.normalize import to_float
from core.scatter_map import render_pie, STAGE_COLORS, STAGE_LABELS
from ui import state
from ui.shell import page_shell


_ORDER = {
    "not_started": 0, "excavation": 1, "blinding": 2,
    "reinforcement": 3, "formwork": 4, "pouring": 5,
    "curing": 6, "finishing": 7, "complete": 8,
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


def _stage_for_activity(a: str) -> str | None:
    a = (a or "").lower().strip()
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


def _infer_stage(activities, prog_sum, prog_n) -> str:
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
    out.sort(key=lambda x: (
        int(x["building"]) if x["building"].isdigit() else 10**9
    ))
    return out


_ZONES_CSS = """
<style>
.dpr-toolbar {
  display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
  margin-bottom: 6px;
}
.dpr-search-wrap { flex: 1; min-width: 200px; }
.dpr-search-btn.q-btn {
  min-height: 32px !important; height: 32px !important;
  padding: 0 14px !important; font-size: 11.5px !important;
  font-weight: 700 !important;
  border: 1px solid rgba(242,116,12,0.42) !important;
  color: #F2740C !important;
  background: transparent !important;
  border-radius: 8px !important;
  letter-spacing: 0.05em;
}
.dpr-search-btn.q-btn:hover {
  background: rgba(242,116,12,0.08) !important;
  border-color: #F2740C !important;
}
.dpr-zoom-group {
  display: inline-flex;
  background: #0c0c0f;
  border: 1px solid rgba(242,116,12,0.28);
  border-radius: 8px;
  overflow: hidden;
}
.dpr-zoom-btn.q-btn {
  background: transparent !important;
  border: none !important;
  border-right: 1px solid rgba(242,116,12,0.15) !important;
  border-radius: 0 !important;
  color: #85858c !important;
  min-height: 32px !important;
  height: 32px !important;
  min-width: 44px !important;
  padding: 0 10px !important;
  font-size: 11.5px !important;
  font-weight: 700 !important;
}
.dpr-zoom-btn.q-btn:last-child { border-right: none !important; }
.dpr-zoom-btn.q-btn:hover {
  color: #F2740C !important;
  background: rgba(242,116,12,0.06) !important;
}
.dpr-zoom-btn.q-btn.dpr-zoom-active {
  background: rgba(242,116,12,0.16) !important;
  color: #F2740C !important;
}
.dpr-clear-btn.q-btn {
  min-height: 32px !important; height: 32px !important;
  padding: 0 12px !important; font-size: 11.5px !important;
  border-color: rgba(255,77,106,0.35) !important;
  color: #ff4d6a !important;
}
.dpr-clear-btn.q-btn:hover {
  background: rgba(255,77,106,0.08) !important;
  border-color: #ff4d6a !important;
}
.dpr-search-status {
  font-size: 11px; color: #85858c;
  padding: 2px 2px 6px 2px; min-height: 18px;
}
.dpr-search-status b { color: #F2740C; }
.dpr-search-status.err { color: #ff4d6a; }
.dpr-zoom-hint {
  font-size: 10px; color: #4f4f56;
  padding: 0 2px 8px 2px; letter-spacing: 0.02em;
}
.dpr-zoom-hint kbd {
  background: rgba(242,116,12,0.10);
  color: #85858c;
  border-radius: 3px;
  padding: 1px 5px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 9.5px;
  border: 1px solid rgba(242,116,12,0.20);
}

.dpr-viewport {
  width: 100%;
  max-height: 72vh;
  overflow: auto;
  border: 1px solid rgba(242,116,12,0.28);
  border-radius: 12px;
  background: #08080a;
  -webkit-overflow-scrolling: touch;
  touch-action: pan-x pan-y;
  position: relative;
}
.dpr-canvas {
  position: relative;
  width: 100%;
  transition: width .15s ease;
  min-height: 200px;
}
.dpr-canvas img.dpr-scatter-img {
  display: block;
  width: 100%;
  height: auto;
  pointer-events: none;
  user-select: none;
  -webkit-user-drag: none;
}

.dpr-hotspot {
  position: absolute;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  cursor: pointer;
  background: transparent;
  border: 2px solid transparent;
  z-index: 4;
  transition: background-color .12s ease, border-color .12s ease,
              box-shadow .2s ease;
  -webkit-tap-highlight-color: transparent;
}
.dpr-hotspot:hover {
  background: rgba(242,116,12,0.14);
  border-color: rgba(242,116,12,0.65);
}
.dpr-hotspot.selected {
  background: rgba(242,116,12,0.16);
  border-color: #F2740C;
  box-shadow: 0 0 0 3px rgba(242,116,12,0.28),
              0 0 24px rgba(242,116,12,0.55);
  animation: dpr-hs-pulse 1.8s ease-in-out infinite;
}
@keyframes dpr-hs-pulse {
  0%, 100% {
    box-shadow: 0 0 0 3px rgba(242,116,12,0.28),
                0 0 24px rgba(242,116,12,0.55);
  }
  50% {
    box-shadow: 0 0 0 3px rgba(242,116,12,0.28),
                0 0 34px rgba(242,116,12,0.85);
  }
}

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
  position: sticky; top: 68px;
  max-height: calc(100vh - 84px);
  overflow-y: auto;
}
@media (max-width: 960px) {
  .dpr-sel-panel { position: relative; top: 0; max-height: none; }
}
.dpr-sel-empty {
  color: #4f4f56; font-size: 12px;
  text-align: center; padding: 36px 12px;
  line-height: 1.6; font-style: italic;
}
.dpr-sel-band {
  display: flex; align-items: center; justify-content: space-between;
  gap: 8px; padding: 7px 11px; border-radius: 8px;
  margin-bottom: 12px; color: #050506;
  font-size: 10px; font-weight: 800;
  letter-spacing: 0.12em; text-transform: uppercase;
}
.dpr-sel-title {
  color: #e8e8ea; font-size: 22px; font-weight: 800;
  letter-spacing: -0.02em; margin-bottom: 2px;
}
.dpr-sel-sub { color: #85858c; font-size: 11px; margin-bottom: 14px; }
.dpr-sel-row {
  display: flex; justify-content: space-between; align-items: baseline;
  gap: 8px; padding: 8px 0;
  border-bottom: 1px solid rgba(242,116,12,0.08);
  font-size: 12px;
}
.dpr-sel-row:last-of-type { border-bottom: none; }
.dpr-sel-key { color: #85858c; }
.dpr-sel-val { color: #e8e8ea; font-weight: 700; text-align: right; }
.dpr-sel-val.orange { color: #F2740C; }
.dpr-sel-val.warn   { color: #ffb020; }
.dpr-sel-val.risk   { color: #ff4d6a; }
.dpr-sel-val.ok     { color: #F2740C; }
.dpr-sel-prog {
  height: 6px; background: rgba(255,255,255,0.05);
  border-radius: 999px; overflow: hidden; margin: 6px 0 4px 0;
}
.dpr-sel-prog-fill { height: 100%; border-radius: 999px; }
.dpr-sel-acts { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; }
.dpr-sel-act {
  font-size: 10px; color: #c8c8cc;
  background: rgba(242,116,12,0.07);
  border: 1px solid rgba(242,116,12,0.18);
  padding: 2px 7px; border-radius: 4px;
}

.dpr-points {
  background: linear-gradient(180deg, #0c0c0f 0%, #08080a 100%);
  border: 1px solid rgba(242,116,12,0.20);
  border-radius: 12px;
  padding: 18px 20px;
}
.dpr-pts-section { margin-bottom: 16px; }
.dpr-pts-section:last-child { margin-bottom: 0; }
.dpr-pts-head {
  color: #F2740C; font-size: 10.5px;
  letter-spacing: 0.14em; text-transform: uppercase;
  font-weight: 700; margin-bottom: 8px; padding-bottom: 5px;
  border-bottom: 1px solid rgba(242,116,12,0.10);
}
.dpr-pts-list { list-style: none; margin: 0; padding: 0; }
.dpr-pts-list li {
  position: relative; padding: 5px 0 5px 18px;
  color: #c8c8cc; font-size: 12px; line-height: 1.55;
  border-bottom: 1px solid rgba(242,116,12,0.05);
}
.dpr-pts-list li:last-child { border-bottom: none; }
.dpr-pts-list li:before {
  content: "▸"; position: absolute; left: 0; top: 5px;
  color: #F2740C; font-size: 11px; font-weight: 700;
}
.dpr-pts-list li.warn:before { color: #ffb020; content: "⚠"; }
.dpr-pts-list li.risk:before { color: #ff4d6a; content: "⚠"; }
.dpr-pts-list li.ok:before   { color: #F2740C; content: "✓"; }
.dpr-pts-list b { color: #e8e8ea; font-weight: 700; }
</style>
"""


_ZOOM_JS = """
<script>
(function () {
  function bindViewport() {
    var vp = document.querySelector('.dpr-viewport');
    if (!vp || vp.__dprZoomBound) return;
    vp.__dprZoomBound = true;

    vp.addEventListener('wheel', function (e) {
      if (!(e.ctrlKey || e.metaKey)) return;
      e.preventDefault();
      var delta = e.deltaY < 0 ? 0.18 : -0.18;
      if (typeof emitEvent === 'function') {
        emitEvent('dpr_zoom_delta', {delta: delta});
      }
    }, {passive: false});

    var lastDist = 0;
    vp.addEventListener('touchstart', function (e) {
      if (e.touches && e.touches.length === 2) {
        lastDist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
      }
    }, {passive: true});
    vp.addEventListener('touchmove', function (e) {
      if (e.touches && e.touches.length === 2 && lastDist > 0) {
        var dist = Math.hypot(
          e.touches[0].clientX - e.touches[1].clientX,
          e.touches[0].clientY - e.touches[1].clientY
        );
        var ratio = dist / lastDist;
        if (ratio > 1.08 || ratio < 0.92) {
          if (typeof emitEvent === 'function') {
            emitEvent('dpr_zoom_mult', {mult: ratio});
          }
          lastDist = dist;
        }
      }
    }, {passive: true});
    vp.addEventListener('touchend', function () { lastDist = 0; }, {passive: true});
    vp.addEventListener('touchcancel', function () { lastDist = 0; }, {passive: true});
  }

  bindViewport();
  new MutationObserver(bindViewport).observe(document.body, {
    childList: true, subtree: true
  });
})();
</script>
"""


def _render_selected(z: dict | None) -> None:
    if z is None:
        ui.html(
            '<div class="dpr-sel-empty">'
            'Tap a slice on the chart — or search a building — '
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


def _build_points(zones, rpt) -> dict:
    total_crew = sum(z["crew"] for z in zones)
    total_rows = sum(z["rows"] for z in zones)
    total_acts = len({a for z in zones for a in z["activities"]})
    stage_counts = Counter(z["stage"] for z in zones)
    top_stage = stage_counts.most_common(1)[0] if stage_counts else ("not_started", 0)

    top_crew = sorted(
        [z for z in zones if z["crew"] > 0], key=lambda z: -z["crew"]
    )[:3]
    sorted_stage = sorted(zones, key=lambda z: _ORDER.get(z["stage"], 0))
    latest = sorted_stage[-1] if sorted_stage else None

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
        watch.append(("warn",
            f"<b>{len(stalled)}</b> zone(s) at excavation with crew assigned "
            f"— possible stall: {', '.join(z['id'] for z in stalled)}"))
    if high_crew_low:
        top = high_crew_low[0]
        watch.append(("warn",
            f"<b>{top['id']}</b> has {top['crew']} crew but only "
            f"{top['avg_progress']:.0f}% progress — resources may be idle"))
    if low_conf:
        watch.append(("warn",
            f"<b>{len(low_conf)}</b> zone(s) contain low-confidence rows — "
            f"verify: {', '.join(z['id'] for z in low_conf[:5])}"))
    if n_hard:
        watch.append(("risk",
            f"<b>{n_hard}</b> hard conflict(s) across source files"))
    if not watch:
        watch.append(("ok",
            "No material issues detected — data is consistent across sources"))

    actions: list[str] = []
    if stalled:
        actions.append(f"Reallocate crew to accelerate "
                       f"{', '.join(z['id'] for z in stalled[:3])}")
    if high_crew_low:
        actions.append(f"Audit productivity in <b>{high_crew_low[0]['id']}</b>")
    if low_conf:
        actions.append("Verify flagged zones in Reconcile Sources before export")
    if latest and _ORDER[latest["stage"]] >= _ORDER["pouring"]:
        actions.append(f"Schedule cube tests / curing verification for "
                       f"<b>{latest['id']}</b>")
    if not actions:
        actions.append("Continue as planned — no corrective action required")

    return {"overview": overview, "watch": watch, "actions": actions}


def render():
    with page_shell(
        active="zones",
        title="Site Overview",
        subtitle=(
            "Interactive pie chart of crew distribution by building. "
            "Search a building to highlight its slice — tap any slice "
            "to inspect it."
        ),
    ):
        ui.add_head_html(_ZONES_CSS, shared=False)
        ui.add_body_html(_ZOOM_JS)

        rpt = state.report()
        if rpt is None:
            with ui.card().classes("dpr-card w-full"):
                ui.label("No report in this session.").classes("dpr-title text-xl")
                ui.label("Aggregate at least one file first — the chart is "
                         "derived from the report's work progress rows.") \
                    .classes("text-white")
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

        W_PX, H_PX = 1400.0, 950.0

        app_state: dict = {
            "highlight_id": None,
            "selection": None,
            "zoom": 1.0,
            "hotspots": [],
        }
        refs: dict = {
            "canvas": None,
            "viewport": None,
            "zoom_btns": {},
            "clear_btn": None,
            "search_input": None,
            "search_status": None,
        }

        with ui.element("div").classes("dpr-toolbar"):
            with ui.element("div").classes("dpr-search-wrap"):
                refs["search_input"] = ui.input(
                    placeholder="Search building — e.g. 78, B78, bldg 78",
                ).props("dense outlined clearable").classes("w-full")

            ui.button("Search",
                      on_click=lambda: _do_search(
                          (refs["search_input"].value or ""))).classes(
                "dpr-search-btn")

            with ui.element("div").classes("dpr-zoom-group"):
                for label, val in [("1×", 1.0), ("2×", 2.0),
                                    ("3×", 3.0), ("4×", 4.0)]:
                    b = ui.button(label,
                                  on_click=lambda v=val: _apply_zoom(v)) \
                        .classes("dpr-zoom-btn")
                    if val == 1.0:
                        b.classes(add="dpr-zoom-active")
                    refs["zoom_btns"][val] = b

            refs["clear_btn"] = ui.button(
                "Clear", on_click=lambda: _clear(),
            ).classes("dpr-clear-btn")
            refs["clear_btn"].set_visibility(False)

        refs["search_status"] = ui.html("").classes("dpr-search-status")

        ui.html(
            '<div class="dpr-zoom-hint">'
            'Zoom: buttons · <kbd>Ctrl</kbd> + scroll on laptop · '
            'two-finger pinch on mobile.'
            '</div>'
        )

        with ui.element("div").classes("dpr-map-wrap"):
            with ui.element("div").classes("dpr-viewport") as viewport:
                refs["viewport"] = viewport
                canvas = ui.element("div").classes("dpr-canvas")
            refs["canvas"] = canvas

            @ui.refreshable
            def map_view():
                canvas.clear()
                png_bytes, hotspots = render_pie(
                    zones, highlight_id=app_state["highlight_id"],
                )
                app_state["hotspots"] = hotspots
                b64 = base64.b64encode(png_bytes).decode("ascii")
                with canvas:
                    ui.html(
                        f'<img class="dpr-scatter-img" '
                        f'src="data:image/png;base64,{b64}" alt="Crew pie"/>'
                    )
                    for hs in hotspots:
                        x_pct = hs["x_px"] / W_PX * 100.0
                        y_pct = hs["y_px"] / H_PX * 100.0
                        size_px = float(hs.get("size_px", 40))
                        z = hs["zone"]
                        is_sel = (
                            app_state["selection"] is not None
                            and app_state["selection"]["id"] == z["id"]
                        )
                        cls = "dpr-hotspot" + (" selected" if is_sel else "")
                        el = ui.element("div").classes(cls)
                        el.style(
                            f"left:{x_pct:.3f}%; top:{y_pct:.3f}%; "
                            f"width:{size_px:.0f}px; height:{size_px:.0f}px;"
                        )
                        el.on("click", lambda zz=z: _pick(zz))

            with ui.element("div").classes("dpr-sel-panel"):
                @ui.refreshable
                def detail_panel():
                    _render_selected(app_state["selection"])
                detail_panel()

        def _refresh_clear_btn() -> None:
            if app_state["selection"] is None:
                refs["clear_btn"].set_visibility(False)
            else:
                refs["clear_btn"].set_visibility(True)

        def _pick(z: dict):
            cur = app_state["selection"]
            if cur is not None and cur["id"] == z["id"]:
                app_state["selection"] = None
                app_state["highlight_id"] = None
            else:
                app_state["selection"] = z
                app_state["highlight_id"] = z["id"]
                _scroll_to(z)
            map_view.refresh()
            detail_panel.refresh()
            _refresh_clear_btn()

        def _clear():
            app_state["selection"] = None
            app_state["highlight_id"] = None
            app_state["zoom"] = 1.0
            _apply_zoom(1.0)
            map_view.refresh()
            detail_panel.refresh()
            refs["search_status"].content = ""
            try:
                refs["search_input"].value = ""
            except Exception:
                pass
            _refresh_clear_btn()

        def _apply_zoom(val: float):
            try:
                val = float(val)
            except (TypeError, ValueError):
                return
            val = max(1.0, min(4.0, val))
            app_state["zoom"] = val
            try:
                refs["canvas"].style(f"width: {int(val * 100)}%;")
            except Exception:
                pass
            for v, b in refs["zoom_btns"].items():
                if abs(v - val) < 0.05:
                    b.classes(add="dpr-zoom-active")
                else:
                    b.classes(remove="dpr-zoom-active")

        _PREFIX_RE = re.compile(
            r'^(building|bldg|block|wtg|b)[\s\-_:\.]*',
            re.IGNORECASE,
        )

        def _normalize_query(q: str) -> str:
            q = (q or "").strip().lower()
            q = _PREFIX_RE.sub("", q)
            return q.strip()

        def _do_search(raw: str):
            q = _normalize_query(raw)

            if not q:
                app_state["highlight_id"] = None
                app_state["selection"] = None
                refs["search_status"].content = ""
                map_view.refresh()
                detail_panel.refresh()
                _refresh_clear_btn()
                return

            match = None
            for tier in ("exact", "prefix", "substr"):
                for z in zones:
                    b = str(z.get("building", "")).lower()
                    i = str(z.get("id", "")).lower()
                    if tier == "exact" and (q == b or q == i):
                        match = z
                        break
                    if tier == "prefix" and (b.startswith(q) or i.startswith(q)):
                        match = z
                        break
                    if tier == "substr" and (q in b or q in i):
                        match = z
                        break
                if match is not None:
                    break

            if match is None:
                app_state["highlight_id"] = None
                app_state["selection"] = None
                refs["search_status"].content = (
                    f'<span class="err">No building matches '
                    f'&quot;{raw}&quot;</span>'
                )
                map_view.refresh()
                detail_panel.refresh()
                _refresh_clear_btn()
                return

            app_state["highlight_id"] = match["id"]
            app_state["selection"] = match
            refs["search_status"].content = (
                f'Highlighting <b>Building '
                f'{match["building"] or match["id"]}</b>'
            )
            map_view.refresh()
            detail_panel.refresh()
            _refresh_clear_btn()
            _scroll_to(match)

        def _scroll_to(z: dict):
            hs = next(
                (h for h in app_state.get("hotspots", [])
                 if h["zone"]["id"] == z["id"]),
                None,
            )
            if hs is None:
                return
            x_px = float(hs["x_px"])
            y_px = float(hs["y_px"])
            try:
                ui.run_javascript(f"""
                    (function() {{
                      var vp = document.querySelector('.dpr-viewport');
                      var c  = document.querySelector('.dpr-canvas');
                      if (!vp || !c) return;
                      var cw = c.clientWidth  || vp.clientWidth;
                      var ch = c.clientHeight || vp.clientHeight;
                      var sx = (cw / {W_PX}) * {x_px};
                      var sy = (ch / {H_PX}) * {y_px};
                      var tx = Math.max(0, sx - vp.clientWidth  / 2);
                      var ty = Math.max(0, sy - vp.clientHeight / 2);
                      vp.scrollTo({{left: tx, top: ty, behavior: 'smooth'}});
                    }})();
                """)
            except Exception:
                pass

        _last_input = {"t": 0.0, "v": "", "done": None}

        def _on_input(e):
            _last_input["t"] = time.monotonic()
            _last_input["v"] = e.value or ""

        def _poll_input():
            t = _last_input["t"]
            v = _last_input["v"]
            if t == 0.0:
                return
            if v == _last_input.get("done"):
                return
            if time.monotonic() - t < 0.35:
                return
            _last_input["done"] = v
            _do_search(v)

        ui.timer(0.15, _poll_input)

        def _on_zoom_delta(e):
            try:
                d = float((e.args or {}).get("delta", 0))
            except Exception:
                return
            _apply_zoom(app_state["zoom"] + d)

        def _on_zoom_mult(e):
            try:
                m = float((e.args or {}).get("mult", 1.0))
            except Exception:
                return
            _apply_zoom(app_state["zoom"] * m)

        ui.on("dpr_zoom_delta", _on_zoom_delta)
        ui.on("dpr_zoom_mult",  _on_zoom_mult)

        try:
            refs["search_input"].on_value_change(_on_input)
        except Exception:
            pass

        map_view()
        _apply_zoom(1.0)

        pts = _build_points(zones, rpt)
        overview_html = "".join(f"<li>{b}</li>" for b in pts["overview"])
        watch_html = "".join(f'<li class="{c}">{b}</li>' for c, b in pts["watch"])
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
