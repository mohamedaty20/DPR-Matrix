"""Matplotlib scatter map — renders server-side, returns PNG + hotspots.

Optional highlight_id dims every non-matching building and rings the match
with an orange glow so a search or click stands out.
"""
from __future__ import annotations

import io

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator


# ── Canvas ────────────────────────────────────────────────────────────────
W_PX = 1600
H_PX = 760
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


def render_scatter(
    zones: list[dict],
    *,
    highlight_id: str | None = None,
) -> tuple[bytes, list[dict]]:
    """
    Returns (png_bytes, hotspots).

    highlight_id — if set, that zone is enlarged and ringed in orange while
    every other zone is dimmed to grey and loses its labels.
    """
    fig = Figure(figsize=(W_PX / DPI, H_PX / DPI), dpi=DPI, facecolor=BG)
    canvas = FigureCanvasAgg(fig)
    ax = fig.add_axes([0.055, 0.11, 0.83, 0.78])
    ax.set_facecolor(BG)

    def _bkey(z):
        b = z.get("building", "")
        return int(b) if str(b).isdigit() else 10**9

    sorted_zones = sorted(zones, key=_bkey)

    x_vals  = list(range(len(sorted_zones)))
    x_labels = [z["building"] or z["id"] for z in sorted_zones]
    y_vals  = [z["crew"] for z in sorted_zones]
    row_vals = [z["rows"] for z in sorted_zones]
    stages  = [z["stage"] for z in sorted_zones]

    y_max = max(y_vals + [1]) * 1.20
    ax.set_ylim(-y_max * 0.10, y_max)

    # Grid
    ax.grid(True, color=GRID, linewidth=0.5, alpha=0.85, linestyle="-")
    ax.set_axisbelow(True)

    # Spines
    for spine in ax.spines.values():
        spine.set_color(GRID)
        spine.set_linewidth(0.7)

    # X-axis — rotated labels so 50+ buildings fit
    ax.tick_params(colors=TEXT_FAINT, labelsize=8, length=0)
    ax.set_xticks(x_vals)
    ax.set_xticklabels(
        [f"B{l}" for l in x_labels],
        rotation=90, fontsize=7.5, color=TEXT_DIM,
        fontweight="bold", ha="center",
    )
    ax.set_xlim(-0.7, len(x_vals) - 0.3 if x_vals else 1)

    # Y-axis
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    for lbl in ax.get_yticklabels():
        lbl.set_fontsize(8.5)
        lbl.set_color(TEXT_DIM)
        lbl.set_fontfamily("monospace")

    # Axis labels
    ax.set_xlabel(
        "BUILDING", fontsize=8.5, color=TEXT_FAINT,
        labelpad=8, fontweight="bold",
    )
    ax.set_ylabel(
        "CREW ON SITE", fontsize=8.5, color=TEXT_FAINT,
        labelpad=10, fontweight="bold",
    )

    # Title
    total_crew = sum(y_vals)
    ax.text(
        -0.045, 1.055, "SITE MANPOWER MAP",
        transform=ax.transAxes, fontsize=11, color=ORANGE,
        fontweight="bold", va="bottom",
    )
    ax.text(
        -0.045, 1.010,
        f"{len(zones)} building(s)  ·  {total_crew} total crew  ·  "
        f"size = work rows  ·  colour = stage",
        transform=ax.transAxes, fontsize=8, color=TEXT_FAINT, va="bottom",
    )

    # ── Scatter ──────────────────────────────────────────────────────
    has_hl = highlight_id is not None

    for x, y, rows, stage, z in zip(x_vals, y_vals, row_vals, stages, sorted_zones):
        is_match = (has_hl and z["id"] == highlight_id)
        is_dim   = has_hl and not is_match

        color = STAGE_COLORS.get(stage, "#4f4f56")

        # Size — significantly smaller than before
        size = 42 + min(rows, 12) * 16       # range 42..234

        if is_dim:
            ax.scatter(
                x, y, s=size * 0.55, c=DIM_GREY,
                alpha=0.30, edgecolors=DIM_GREY,
                linewidths=0.6, zorder=2,
            )
            continue

        if is_match:
            # Glow rings behind
            ax.scatter(
                x, y, s=size * 5.5, c=ORANGE, alpha=0.10,
                edgecolors="none", zorder=1,
            )
            ax.scatter(
                x, y, s=size * 2.6, c="none", edgecolors=ORANGE,
                linewidths=2.2, alpha=0.85, zorder=5,
            )

        # Main dot
        ax.scatter(
            x, y, s=size * (1.5 if is_match else 1.0),
            c=color, alpha=0.95,
            edgecolors=color, linewidths=1.2, zorder=3,
        )
        # Inner ring
        ax.scatter(
            x, y, s=size * 0.28 * (1.5 if is_match else 1.0),
            c="none", edgecolors="#050506", linewidths=0.7,
            alpha=0.55, zorder=4,
        )

        # Crew number — inside the dot
        crew_fs = 9 if is_match else 7.5
        ax.text(
            x, y, f"{y}",
            ha="center", va="center",
            fontsize=crew_fs,
            color="#050506" if is_match else "#ffffff",
            fontweight="bold", zorder=6,
        )
        # Building number — small label just above the dot
        ax.text(
            x, y + y_max * 0.035,
            f"B{x_labels[x_vals.index(x)]}",
            ha="center", va="bottom",
            fontsize=7.5, color=ORANGE if is_match else TEXT_DIM,
            fontweight="bold", zorder=6,
        )

    # ── Legend ───────────────────────────────────────────────────────
    if not has_hl:
        present_stages: list[str] = []
        seen: set[str] = set()
        for s in stages:
            if s not in seen:
                present_stages.append(s)
                seen.add(s)

        handles = []
        labels = []
        for s in present_stages:
            handles.append(Line2D(
                [0], [0], marker="o", color="none",
                markerfacecolor=STAGE_COLORS[s],
                markeredgecolor=STAGE_COLORS[s],
                markersize=7,
            ))
            labels.append(STAGE_LABELS[s])

        leg = ax.legend(
            handles, labels,
            loc="upper right",
            frameon=True, facecolor=PANEL, edgecolor=GRID,
            fontsize=7.5, labelcolor=TEXT_DIM,
            ncol=1, borderpad=0.6, handletextpad=0.5,
        )
        leg.get_frame().set_linewidth(0.5)

    # ── Render ───────────────────────────────────────────────────────
    canvas.draw()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=BG)
    png = buf.getvalue()

    # Hotspot pixel positions
    hotspots: list[dict] = []
    for x, y, z in zip(x_vals, y_vals, sorted_zones):
        px, py = ax.transData.transform((x, y))
        y_css = H_PX - py
        hotspots.append({
            "x_px": float(px),
            "y_px": float(y_css),
            "zone": z,
        })

    return png, hotspots
