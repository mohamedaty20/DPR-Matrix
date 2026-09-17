"""Matplotlib pie chart — renders server-side, returns PNG + hotspots.

Replaces the previous scatter rendering. Each slice = one building
(grouped as "Other" past the top 12). Slice size = crew on site.
Slice colour = construction stage. Hotspots are circular overlays
placed at each slice's mid-radius, so the chart stays clickable from
the Zones page.
"""
from __future__ import annotations

import io
import math

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg


# ── Canvas ────────────────────────────────────────────────────────────────
W_PX = 1400
H_PX = 950
DPI = 100

# ── Palette ───────────────────────────────────────────────────────────────
BG         = "#08080a"
PANEL      = "#0c0c0f"
GRID       = "#1a1a1f"
TEXT       = "#e8e8ea"
TEXT_DIM   = "#85858c"
TEXT_FAINT = "#4f4f56"
ORANGE     = "#F2740C"
DIM_GREY   = "#3a3a42"

STAGE_COLORS = {
    "not_started":   "#4f4f56",
    "excavation":    "#d4a017",
    "blinding":      "#4a80c4",
    "reinforcement": "#9a9aa0",
    "formwork":      "#c47a3b",
    "pouring":       "#F2740C",
    "curing":        "#8a4ab0",
    "finishing":     "#b06b3a",
    "complete":      "#0a8a3b",
}
STAGE_LABELS = {
    "not_started":   "Not Started",
    "excavation":    "Excavation",
    "blinding":      "Blinding",
    "reinforcement": "Reinforcement",
    "formwork":      "Formwork",
    "pouring":       "Pouring",
    "curing":        "Curing",
    "finishing":     "Finishing",
    "complete":      "Complete",
}


def _dim_color(hex_color: str, factor: float = 0.32) -> str:
    h = (hex_color or "#4f4f56").lstrip("#")
    if len(h) != 6:
        h = "4f4f56"
    try:
        r = int(h[0:2], 16); g = int(h[2:4], 16); b = int(h[4:6], 16)
    except ValueError:
        r, g, b = 0x4f, 0x4f, 0x56
    br, bg_, bb = 0x08, 0x08, 0x0a
    r = int(r * factor + br * (1 - factor))
    g = int(g * factor + bg_ * (1 - factor))
    b = int(b * factor + bb * (1 - factor))
    return f"#{r:02x}{g:02x}{b:02x}"


_MAX_SLICES = 12


def render_pie(
    zones: list[dict],
    *,
    highlight_id: str | None = None,
) -> tuple[bytes, list[dict]]:
    """
    zones — list of dicts with keys: id, building, crew, rows, stage.
    highlight_id — if set, that slice is exploded and every other slice
                   is dimmed to a low-saturation grey.

    Returns (png_bytes, hotspots).
    """
    zs = [z for z in zones if (z.get("crew") or 0) > 0]
    if not zs:
        zs = [dict(z, crew=(z.get("rows") or 1))
              for z in zones if (z.get("rows") or 0) > 0]

    zs.sort(key=lambda z: -(z.get("crew") or 0))

    top = list(zs[:_MAX_SLICES])
    rest = zs[_MAX_SLICES:]
    if rest:
        top.append({
            "id": "__OTHER__",
            "building": "Other",
            "crew": sum(z.get("crew") or 0 for z in rest),
            "rows": sum(z.get("rows") or 0 for z in rest),
            "stage": "not_started",
            "is_other": True,
        })

    # ── Empty state ───────────────────────────────────────────────────
    if not top:
        fig = Figure(figsize=(W_PX / DPI, H_PX / DPI), dpi=DPI, facecolor=BG)
        canvas = FigureCanvasAgg(fig)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_facecolor(BG)
        ax.axis("off")
        ax.text(0.5, 0.5, "No zones to display",
                ha="center", va="center", color=TEXT_DIM,
                fontsize=14, transform=ax.transAxes)
        canvas.draw()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", facecolor=BG)
        return buf.getvalue(), []

    sizes = [max(float(z.get("crew") or 0), 0.001) for z in top]
    total = sum(sizes)

    has_hl = highlight_id is not None
    colors_list: list[str] = []
    explode: list[float] = []
    for z in top:
        is_match = has_hl and z["id"] == highlight_id
        base = (DIM_GREY if z.get("is_other")
                else STAGE_COLORS.get(z.get("stage") or "", "#4f4f56"))
        colors_list.append(_dim_color(base, 0.32) if (has_hl and not is_match)
                           else base)
        explode.append(0.09 if is_match else 0.0)

    # ── Render ────────────────────────────────────────────────────────
    fig = Figure(figsize=(W_PX / DPI, H_PX / DPI), dpi=DPI, facecolor=BG)
    canvas = FigureCanvasAgg(fig)

    # Pie takes the left ~64% of the canvas; legend fills the right.
    ax = fig.add_axes([0.02, 0.03, 0.64, 0.94])
    ax.set_facecolor(BG)

    wedges, _texts = ax.pie(
        sizes,
        colors=colors_list,
        explode=explode,
        startangle=90,
        counterclock=False,
        wedgeprops={"linewidth": 1.8, "edgecolor": "#050506"},
        radius=1.0,
    )

    # In-slice percentages for large slices only
    for wedge, sz in zip(wedges, sizes):
        pct = sz / total * 100 if total else 0
        if pct < 5:
            continue
        theta_mid = math.radians((wedge.theta1 + wedge.theta2) / 2)
        cx, cy = wedge.center
        tx = cx + wedge.r * 0.62 * math.cos(theta_mid)
        ty = cy + wedge.r * 0.62 * math.sin(theta_mid)
        ax.text(tx, ty, f"{pct:.0f}%",
                ha="center", va="center",
                fontsize=11, fontweight="bold", color="#ffffff")

    ax.set_title(
        "Crew distribution by building",
        color=ORANGE, fontsize=12, fontweight="bold", pad=8,
    )

    # Legend on the right — building number + crew count
    legend_labels = [
        f'{z.get("building") or z["id"]}  ·  {int(z.get("crew") or 0)}'
        for z in top
    ]
    ax.legend(
        wedges, legend_labels,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=False,
        fontsize=8.5,
        labelcolor=TEXT_DIM,
        handlelength=0.9,
        handleheight=0.9,
        borderpad=0.2,
        labelspacing=0.55,
    )

    canvas.draw()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=BG)
    png = buf.getvalue()

    # ── Hotspots — placed at 62% radius inside each wedge ─────────────
    hotspots: list[dict] = []
    for wedge, z in zip(wedges, top):
        theta_mid = math.radians((wedge.theta1 + wedge.theta2) / 2)
        cx, cy = wedge.center
        px_data = cx + wedge.r * 0.62 * math.cos(theta_mid)
        py_data = cy + wedge.r * 0.62 * math.sin(theta_mid)
        display_x, display_y = ax.transData.transform((px_data, py_data))
        y_css = H_PX - display_y
        arc_deg = abs(wedge.theta2 - wedge.theta1)
        slice_frac = arc_deg / 360.0
        diameter = max(30.0, min(78.0, slice_frac * W_PX * 0.85))
        hotspots.append({
            "x_px": float(display_x),
            "y_px": float(y_css),
            "size_px": float(diameter),
            "zone": z,
        })

    return png, hotspots
