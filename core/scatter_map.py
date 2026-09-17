"""Matplotlib scatter map — renders server-side, returns PNG + hotspots.

The figure is drawn at a fixed pixel size (1000×600) so that data
coordinates can be transformed to pixel coordinates and returned alongside
the PNG. The UI overlays transparent clickable hotspots at those positions.
"""
from __future__ import annotations

import io

import matplotlib
matplotlib.use("Agg")   # headless — no display server on Render
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.patches import FancyBboxPatch

from core.normalize import to_float


# ── Canvas ────────────────────────────────────────────────────────────────
W_PX = 1000
H_PX = 620
DPI = 100

# ── Palette ───────────────────────────────────────────────────────────────
BG         = "#08080a"
PANEL      = "#0c0c0f"
GRID       = "#1a1a1f"
TEXT       = "#e8e8ea"
TEXT_DIM   = "#85858c"
TEXT_FAINT = "#4f4f56"
ORANGE     = "#F2740C"
ORANGE_DIM = "#C75A00"

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


def render_scatter(zones: list[dict]) -> tuple[bytes, list[dict]]:
    """
    Returns (png_bytes, hotspots).
    hotspots = [{"x_px": float, "y_px": float, "zone": dict}, ...]
      · x_px / y_px are in IMAGE pixel space (origin top-left) so they can
        be laid out with CSS `left: X%` / `top: Y%` on top of the <img>.
    """
    fig = Figure(figsize=(W_PX / DPI, H_PX / DPI), dpi=DPI, facecolor=BG)
    canvas = FigureCanvasAgg(fig)
    ax = fig.add_axes([0.075, 0.11, 0.80, 0.78])   # left, bottom, w, h
    ax.set_facecolor(BG)

    # ── X data: building numbers, sorted ─────────────────────────────
    sorted_zones = sorted(
        zones,
        key=lambda z: int(z["building"]) if z["building"].isdigit() else 10**9,
    )
    x_vals = list(range(len(sorted_zones)))
    x_labels = [z["building"] or z["id"] for z in sorted_zones]
    y_vals = [z["crew"] for z in sorted_zones]
    row_vals = [z["rows"] for z in sorted_zones]
    stages = [z["stage"] for z in sorted_zones]

    y_max = max(y_vals + [1]) * 1.18
    ax.set_ylim(-y_max * 0.08, y_max)

    # ── Grid ─────────────────────────────────────────────────────────
    ax.grid(True, color=GRID, linewidth=0.6, alpha=0.9, linestyle="-")
    ax.set_axisbelow(True)

    # ── Axes styling ─────────────────────────────────────────────────
    for spine in ax.spines.values():
        spine.set_color(GRID)
        spine.set_linewidth(0.8)
    ax.tick_params(colors=TEXT_FAINT, labelsize=9, length=0)
    ax.set_xticks(x_vals)
    ax.set_xticklabels(
        [f"B{l}" for l in x_labels],
        fontsize=10, color=TEXT_DIM, fontweight="bold",
    )
    ax.set_xlim(-0.6, len(x_vals) - 0.4 if x_vals else 1)
    ax.yaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=6))
    for lbl in ax.get_yticklabels():
        lbl.set_fontsize(9)
        lbl.set_color(TEXT_DIM)
        lbl.set_fontfamily("monospace")

    # ── Axis labels ──────────────────────────────────────────────────
    ax.set_xlabel(
        "BUILDING", fontsize=9, color=TEXT_FAINT,
        labelpad=8, fontweight="bold", letter_spacing=1.5,
    )
    ax.set_ylabel(
        "CREW ON SITE", fontsize=9, color=TEXT_FAINT,
        labelpad=10, fontweight="bold",
    )

    # ── Title (drawn as ax text so it stays inside the axes) ─────────
    total_crew = sum(y_vals)
    ax.text(
        -0.045, 1.055,
        "SITE MANPOWER MAP",
        transform=ax.transAxes,
        fontsize=11, color=ORANGE, fontweight="bold",
        letter_spacing=2.0, va="bottom",
    )
    ax.text(
        -0.045, 1.012,
        f"{len(zones)} building(s)  ·  {total_crew} total crew  ·  "
        f"marker size = work rows",
        transform=ax.transAxes,
        fontsize=8.5, color=TEXT_FAINT, va="bottom",
    )

    # ── Scatter ──────────────────────────────────────────────────────
    for x, y, rows, stage in zip(x_vals, y_vals, row_vals, stages):
        color = STAGE_COLORS.get(stage, "#4f4f56")
        # marker size = rows, bounded
        size = 120 + min(rows, 12) * 55

        ax.scatter(
            x, y,
            s=size,
            c=color,
            alpha=0.85,
            edgecolors=color,
            linewidths=1.8,
            zorder=3,
        )
        # Inner ring for polish
        ax.scatter(
            x, y,
            s=size * 0.28,
            c="none",
            edgecolors=color,
            linewidths=0.9,
            alpha=0.7,
            zorder=4,
        )
        # Crew value above
        ax.text(
            x, y + y_max * 0.045,
            f"{y}",
            ha="center", va="bottom",
            fontsize=10, color=TEXT, fontweight="bold",
            zorder=5,
        )

    # ── Legend ───────────────────────────────────────────────────────
    present_stages = []
    seen = set()
    for s in stages:
        if s not in seen:
            present_stages.append(s)
            seen.add(s)

    handles = []
    labels = []
    for s in present_stages:
        from matplotlib.lines import Line2D
        handles.append(Line2D(
            [0], [0], marker="o", color="none",
            markerfacecolor=STAGE_COLORS[s],
            markeredgecolor=STAGE_COLORS[s],
            markersize=9,
        ))
        labels.append(STAGE_LABELS[s])

    leg = ax.legend(
        handles, labels,
        loc="upper right",
        frameon=True,
        facecolor=PANEL,
        edgecolor=GRID,
        fontsize=8,
        labelcolor=TEXT_DIM,
        ncol=1,
        borderpad=0.7,
        handletextpad=0.6,
    )
    leg.get_frame().set_linewidth(0.6)

    # ── Render to PNG ────────────────────────────────────────────────
    canvas.draw()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=BG)
    png = buf.getvalue()

    # ── Compute hotspot pixel positions ──────────────────────────────
    hotspots = []
    for x, y, z in zip(x_vals, y_vals, sorted_zones):
        px, py = ax.transData.transform((x, y))
        y_css = H_PX - py   # matplotlib origin is bottom-left
        hotspots.append({
            "x_px": float(px),
            "y_px": float(y_css),
            "zone": z,
        })

    return png, hotspots
