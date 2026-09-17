"""Zone Progress Board — interactive site map derived from the report.

No user input. Buildings are plotted on a blueprint-style canvas, coloured
by inferred construction stage, sized by crew count. Click a node to see
that zone's status. Below the map: short, decision-oriented bullet points.
"""
from __future__ import annotations

from collections import Counter

from nicegui import ui

from core.normalize import to_float
from ui import state
from ui.shell import page_shell


# ═══════════════════════════════════════════════════════════════════════════
# Stage vocabulary
# ═══════════════════════════════════════════════════════════════════════════
STAGES: list[tuple[str, str, str]] = [
    ("not_started",   "Not Started",   "#4f4f56"),
    ("excavation",    "Excavation",    "#d4a017"),
    ("blinding",      "Blinding",      "#4a80c4"),
    ("reinforcement", "Reinforcement", "#9a9aa0"),
    ("formwork",      "Formwork",      "#c47a3b"),
    ("pouring",       "Pouring",       "#F2740C"),
    ("curing",        "Curing",        "#8a4ab0"),
    ("finishing",     "Finishing",     "#b06b3a"),
    ("complete",      "Complete",      "#0a8a3b"),
]
_ORDER = {k: i for i, (k, _, _) in enumerate(STAGES)}
_LABEL = {k: l for k, l, _ in STAGES}
_COLOR = {k: c for k, _, c in STAGES}


_ACTIVITY_TO_STAGE = {
    "excavation":       "excavation",
    "backfilling":      "excavation",
    "blinding":         "blinding",
    "steel fixing":     "reinforcement",
    "reinforcement":    "reinforcement",
    "formwork":         "formwork",
    "concrete works":   "pouring",
    "concreting":       "pouring",
    "curing":           "curing",
    "waterproofing":    "finishing",
    "mortar works":     "finishing",
    "brickworks":       "finishing",
    "plastering":       "finishing",
    "sealer works":     "finishing",
    "painting":         "finishing",
    "tiling":           "finishing",
    "gypsum works":     "finishing",
    "ceiling works":    "finishing",
    "carpentry":        "finishing",
    "electrical":       "finishing",
    "plumbing":         "finishing",
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


# ═══════════════════════════════════════════════════════════════════════════
# Zone derivation
# ═══════════════════════════════════════════════════════════════════════════
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
            "id": key,
            "label": g["label"],
            "building": g["building"],
            "floors": sorted(g["floors"], key=_floor_sort),
            "rows": g["rows"],
            "activities": g["activities"],
            "top_activity": top,
            "crew": g["crew"],
            "stage": stage,
            "avg_progress": avg,
            "low_conf": g["low_conf"],
        })

    out.sort(key=lambda x: (-x["crew"], x["id"]))
    return out


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


# ═══════════════════════════════════════════════════════════════════════════
# Map layout — positions on a blueprint canvas (percent coordinates)
# ═══════════════════════════════════════════════════════════════════════════
def _layout_positions(n: int) -> list[tuple[float, float]]:
    """Returns [(x%, y%), ...] for n zones, in a staggered site-plan grid."""
    if n == 0:
        return []
    if n == 1:
        return [(50.0, 50.0)]

    cols = min(4, max(2, (n + 1) // 2))
    rows = (n + cols - 1) // cols

    # Horizontal padding: 12% – 88%
    # Vertical padding: 20% – 80%
    x_pad_l, x_pad_r = 12.0, 88.0
    y_pad_t, y_pad_b = 22.0, 78.0
    x_span = x_pad_r - x_pad_l
    y_span = y_pad_b - y_pad_t

    positions = []
    for i in range(n):
        row = i // cols
        col = i % cols
        items_this_row = cols if row < rows - 1 else (n - (rows - 1) * cols)
        if items_this_row < cols:
            # Center the last row
            offset = (cols - items_this_row) / 2.0
        else:
            offset = 0.0
        x = x_pad_l + ((col + offset + 0.5) / cols) * x_span
        # Stagger every other row slightly
        if row % 2 == 1:
            x += x_span / cols * 0.10
        y = y_pad_t + ((row + 0.5) / rows) * y_span
        positions.append((x, y))
    return positions


# ═══════════════════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════════════════
_ZONES_CSS = """
<style>
.dpr-map-wrap {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 14px;
  margin-bottom: 14px;
}
@media (max-width: 900px) {
  .dpr-map-wrap { grid-template-columns: 1fr; }
}

.dpr-map-canvas {
  position: relative;
  width: 100%;
  aspect-ratio: 5 / 3;
  min-height: 360px;
  background:
    linear-gradient(0deg,
      rgba(242,116,12,0.07) 1px, transparent 1px) 0 0 / 32px 32px,
    linear-gradient(90deg,
      rgba(242,116,12,0.07) 1px, transparent 1px) 0 0 / 32px 32px,
    radial-gradient(circle at 50% 50%,
      rgba(242,116,12,0.04) 0%, transparent 65%),
    #08080a;
  border: 1px solid rgba(242,116,12,0.28);
  border-radius: 12px;
  overflow: hidden;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

/* SVG overlay for perimeter + connection lines */
.dpr-map-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

/* Central site hub */
.dpr-map-hub {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 46px; height: 46px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(242,116,12,0.22) 0%, rgba(242,116,12,0.02) 70%);
  border: 1px solid rgba(242,116,12,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 8.5px;
  font-weight: 800;
  letter-spacing: 0.14em;
  color: #F2740C;
  pointer-events: none;
  z-index: 2;
  animation: dpr-hub-pulse 2.6s ease-in-out infinite;
}
@keyframes dpr-hub-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(242,116,12,0.28); }
  50%      { box-shadow: 0 0 0 14px rgba(242,116,12,0.00); }
}

/* Building nodes */
.dpr-map-node {
  position: absolute;
  transform: translate(-50%, -50%);
  cursor: pointer;
  transition: transform .15s ease, z-index 0s;
  z-index: 3;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.dpr-map-node:hover { transform: translate(-50%, -50%) scale(1.10); z-index: 20; }
.dpr-map-node.selected { z-index: 15; }
.dpr-map-node.selected .dpr-map-node-shape {
  box-shadow: 0 0 0 3px rgba(242,116,12,0.35),
              0 0 26px rgba(242,116,12,0.5);
}

.dpr-map-node-shape {
  width: clamp(46px, 6.4vw, 68px);
  height: clamp(46px, 6.4vw, 68px);
  border-radius: 10px;
  border: 1.5px solid;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  letter-spacing: -0.02em;
  position: relative;
  transition: box-shadow .18s ease;
  backdrop-filter: blur(2px);
}
.dpr-map-node-num {
  font-size: clamp(15px, 1.6vw, 20px);
  line-height: 1;
}
.dpr-map-node-stage {
  font-size: 8px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-top: 2px;
  opacity: 0.85;
  font-weight: 700;
}
.dpr-map-node-crew {
  font-size: 10px;
  font-weight: 700;
  color: #e8e8ea;
  background: rgba(0,0,0,0.65);
  border: 1px solid rgba(242,116,12,0.28);
  padding: 1px 6px;
  border-radius: 999px;
  white-space: nowrap;
}

/* Selected zone detail panel (right column) */
.dpr-sel-panel {
  background: linear-gradient(180deg, #0c0c0f 0%, #08080a 100%);
  border: 1px solid rgba(242,116,12,0.28);
  border-radius: 12px;
  padding: 16px 18px;
  align-self: start;
  position: sticky;
  top: 68px;
  max-height: calc(100vh - 84px);
  overflow-y: auto;
}
.dpr-sel-empty {
  color: #4f4f56;
  font-size: 12px;
  text-align: center;
  padding: 40px 10px;
  line-height: 1.6;
  font-style: italic;
}
.dpr-sel-band {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 10px;
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
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.02em;
  margin-bottom: 4px;
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
  padding: 7px 0;
  border-bottom: 1px solid rgba(242,116,12,0.08);
  font-size: 12px;
}
.dpr-sel-row:last-of-type { border-bottom: none; }
.dpr-sel-key { color: #85858c; }
.dpr-sel-val { color: #e8e8ea; font-weight: 700; text-align: right; }
.dpr-sel-val.orange { color: #F2740C; }
.dpr-sel-val.warn   { color: #ffb020; }
.dpr-sel-val.risk   { color: #ff4d6a; }
.dpr-sel-prog {
  height: 6px;
  background: rgba(255,255,255,0.05);
  border-radius: 999px;
  overflow: hidden;
  margin: 6px 0 4px 0;
}
.dpr-sel-prog-fill {
  height: 100%;
  border-radius: 999px;
}
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
.dpr-pts-section {
  margin-bottom: 16px;
}
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
.dpr-pts-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
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
  left: 0;
  top: 5px;
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
# Site map
# ═══════════════════════════════════════════════════════════════════════════
def _render_map(zones: list[dict], selection: dict, on_select) -> None:
    positions = _layout_positions(len(zones))

    # SVG overlay: perimeter + connector lines hub → each node
    lines = ""
    for (x, y) in positions:
        lines += (
            f'<line x1="50" y1="50" x2="{x:.2f}" y2="{y:.2f}" '
            f'stroke="rgba(242,116,12,0.13)" stroke-width="0.18" '
            f'stroke-dasharray="1.2 1.2"/>'
        )
    svg = (
        f'<svg class="dpr-map-svg" viewBox="0 0 100 100" '
        f'preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">'
        f'  <rect x="2" y="3" width="96" height="94" fill="none" '
        f'        stroke="rgba(242,116,12,0.28)" stroke-width="0.25" '
        f'        stroke-dasharray="2 2"/>'
        f'  {lines}'
        f'</svg>'
    )
    ui.html(svg)

    # Central site hub
    ui.html('<div class="dpr-map-hub">SITE</div>')

    # Nodes
    for z, (x, y) in zip(zones, positions):
        color = _COLOR.get(z["stage"], "#4f4f56")
        label = _LABEL.get(z["stage"], z["stage"])
        is_sel = selection.get("zone") and selection["zone"]["id"] == z["id"]
        cls = "dpr-map-node" + (" selected" if is_sel else "")

        node = ui.element("div").classes(cls)
        node.style(f"left: {x:.2f}%; top: {y:.2f}%;")
        node.on("click", lambda zz=z: on_select(zz))

        with node:
            ui.html(
                f'<div class="dpr-map-node-shape" '
                f'     style="background:{color}22;border-color:{color};'
                f'            color:{color};">'
                f'  <div class="dpr-map-node-num">{z["label"]}</div>'
                f'  <div class="dpr-map-node-stage">{label}</div>'
                f'</div>'
                f'<div class="dpr-map-node-crew">'
                f'  {z["crew"]} crew'
                f'</div>'
            )


# ═══════════════════════════════════════════════════════════════════════════
# Selected zone detail panel
# ═══════════════════════════════════════════════════════════════════════════
def _render_selected(z: dict | None) -> None:
    if z is None:
        ui.html(
            '<div class="dpr-sel-empty">'
            'Tap a building on the map to see its status, crew, and '
            'activities.'
            '</div>'
        )
        return

    color = _COLOR.get(z["stage"], "#4f4f56")
    label = _LABEL.get(z["stage"], z["stage"])
    prog = z["avg_progress"]
    prog_html = ""
    if prog is None:
        prog_html = (
            '<div style="color:#4f4f56;font-size:11px;padding:6px 0;">'
            'No progress data in source.'
            '</div>'
        )
    else:
        pct = max(0.0, min(100.0, prog))
        prog_html = (
            f'<div class="dpr-sel-prog">'
            f'  <div class="dpr-sel-prog-fill" '
            f'       style="width:{pct:.0f}%;background:{color};"></div>'
            f'</div>'
            f'<div style="color:#85858c;font-size:10.5px;">'
            f'  Avg progress · {pct:.0f}%'
            f'</div>'
        )

    floors_txt = (
        " · ".join(z["floors"]) if z["floors"] else "—"
    )

    conf_cls = "risk" if z["low_conf"] else ""
    conf_val = f'{z["low_conf"]} low-conf row(s)' if z["low_conf"] else "clean"

    acts_html = "".join(
        f'<span class="dpr-sel-act">{a}</span>'
        for a in sorted(z["activities"].keys())
    )

    ui.html(
        f'<div class="dpr-sel-band" style="background:{color};">'
        f'  <span>{label}</span>'
        f'  <span>{z["crew"]} crew</span>'
        f'</div>'
        f'<div class="dpr-sel-title">{z["id"]}</div>'
        f'<div class="dpr-sel-sub">'
        f'  Building {z["building"] or "—"}'
        f'</div>'

        f'<div class="dpr-sel-row">'
        f'  <span class="dpr-sel-key">Crew on site</span>'
        f'  <span class="dpr-sel-val orange">{z["crew"]}</span>'
        f'</div>'
        f'<div class="dpr-sel-row">'
        f'  <span class="dpr-sel-key">Floors</span>'
        f'  <span class="dpr-sel-val">'
        f'    {len(z["floors"])} ({floors_txt})'
        f'  </span>'
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
# Bullet points summary
# ═══════════════════════════════════════════════════════════════════════════
def _build_points(zones: list[dict], rpt) -> dict:
    total_crew = sum(z["crew"] for z in zones)
    total_rows = sum(z["rows"] for z in zones)
    total_acts = len({a for z in zones for a in z["activities"]})

    stage_counts = Counter(z["stage"] for z in zones)
    top_stage = stage_counts.most_common(1)[0] if stage_counts else ("not_started", 0)

    sorted_crew = sorted(zones, key=lambda z: -z["crew"])
    top_crew = [z for z in sorted_crew if z["crew"] > 0][:3]

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

    # ── OVERVIEW ────────────────────────────────────────────────────
    overview = []
    overview.append(
        f"<b>{len(zones)}</b> active zone(s) · "
        f"<b>{total_crew}</b> total crew · "
        f"<b>{total_rows}</b> work rows · "
        f"<b>{total_acts}</b> activities"
    )
    overview.append(
        f"Site predominantly at <b>{_LABEL[top_stage[0]]}</b> stage "
        f"({top_stage[1]} of {len(zones)} zones)"
    )
    if top_crew:
        crew_bits = " · ".join(
            f"<b>{z['id']}</b> ({z['crew']})" for z in top_crew
        )
        overview.append(f"Highest crew concentration: {crew_bits}")

    # ── WATCH ───────────────────────────────────────────────────────
    watch: list[tuple[str, str]] = []
    if stalled:
        names = ", ".join(z["id"] for z in stalled)
        watch.append((
            "warn",
            f"<b>{len(stalled)}</b> zone(s) at excavation with crew assigned "
            f"— possible stall: {names}",
        ))
    if high_crew_low:
        top = high_crew_low[0]
        watch.append((
            "warn",
            f"<b>{top['id']}</b> has {top['crew']} crew but only "
            f"{top['avg_progress']:.0f}% progress — resources may be idle",
        ))
    if low_conf:
        names = ", ".join(z["id"] for z in low_conf[:5])
        watch.append((
            "warn",
            f"<b>{len(low_conf)}</b> zone(s) contain low-confidence rows "
            f"— verify before sign-off: {names}",
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

    # ── ACTIONS ─────────────────────────────────────────────────────
    actions = []
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
                f"({_LABEL[latest['stage']]}) is significant — review sequencing"
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
            "Interactive view of every active zone. Data is derived from "
            "the current report — click any building to inspect its status."
        ),
    ):
        ui.add_head_html(_ZONES_CSS, shared=False)

        rpt = state.report()
        if rpt is None:
            with ui.card().classes("dpr-card w-full"):
                ui.label("No report in this session.").classes("dpr-title text-xl")
                ui.label(
                    "Aggregate at least one file first — the map is derived "
                    "from the report's work progress rows."
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
                'No zones detected in this report.'
                '</div>'
            )
            return

        selection: dict = {"zone": zones[0] if zones else None}

        # ── Map + detail panel ───────────────────────────────────────
        with ui.element("div").classes("dpr-map-wrap"):
            with ui.element("div").classes("dpr-map-canvas"):
                def _on_select(z):
                    selection["zone"] = z
                    detail_panel.refresh()
                    map_canvas.refresh()

                @ui.refreshable
                def map_canvas():
                    _render_map(zones, selection, _on_select)

                @ui.refreshable
                def detail_panel():
                    _render_selected(selection["zone"])

                map_canvas()

            with ui.element("div").classes("dpr-sel-panel"):
                detail_panel()

        # ── Bullet points summary ────────────────────────────────────
        pts = _build_points(zones, rpt)

        overview_html = "".join(
            f"<li>{b}</li>" for b in pts["overview"]
        )
        watch_html = "".join(
            f'<li class="{cls}">{b}</li>' for cls, b in pts["watch"]
        )
        actions_html = "".join(
            f"<li>{b}</li>" for b in pts["actions"]
        )

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

        # ── Footer ───────────────────────────────────────────────────
        with ui.row().classes("gap-2 mt-3 flex-wrap"):
            ui.button("Back to Dashboard",
                      on_click=lambda: ui.navigate.to("/results"))
            ui.button("Reconcile Sources",
                      on_click=lambda: ui.navigate.to("/reconcile"))
