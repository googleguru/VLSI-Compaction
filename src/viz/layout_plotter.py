"""
CIF layout renderer: draws geometry on a white-background matplotlib figure.
Supports before/after snapshots with no overlapping annotations.
"""

import os
import logging
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import Optional, Dict, List, Tuple

from ..io.cif_reader import CIFLayout

logger = logging.getLogger(__name__)

# Consistent layer color palette
_LAYER_COLORS: Dict[str, str] = {
    "POLY":   "#E63946",
    "NDIFF":  "#457B9D",
    "PDIFF":  "#A8DADC",
    "METAL1": "#1D3557",
    "METAL2": "#F4A261",
    "METAL3": "#2A9D8F",
    "VIA1":   "#E9C46A",
    "VIA2":   "#264653",
    "CONT":   "#6D6875",
    "NWELL":  "#B7E4C7",
}
_DEFAULT_COLOR = "#AAAAAA"

_FONT_SIZE  = 9
_LINE_WIDTH = 0.6
_ALPHA      = 0.65


def plot_layout(
    layout: CIFLayout,
    title: str = "",
    ax: Optional[plt.Axes] = None,
    show_legend: bool = True,
) -> plt.Axes:
    fig_created = ax is None
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 5))
        fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    layer_patches: Dict[str, mpatches.Patch] = {}

    for sym in layout.symbols.values():
        for call in sym.calls:
            child = layout.symbols.get(call.symbol_num)
            if child:
                _draw_symbol(ax, child, call.tx, call.ty, layer_patches)
        _draw_symbol(ax, sym, 0, 0, layer_patches)

    for call in layout.top_calls:
        sym = layout.symbols.get(call.symbol_num)
        if sym:
            _draw_symbol(ax, sym, call.tx, call.ty, layer_patches)

    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.tick_params(labelsize=_FONT_SIZE)
    ax.set_xlabel("X (CIF units)", fontsize=_FONT_SIZE)
    ax.set_ylabel("Y (CIF units)", fontsize=_FONT_SIZE)
    if title:
        ax.set_title(title, fontsize=_FONT_SIZE + 1, pad=4)

    if show_legend and layer_patches:
        ax.legend(
            handles=list(layer_patches.values()),
            loc="upper right",
            fontsize=_FONT_SIZE - 1,
            framealpha=0.9,
        )
    return ax


def _draw_symbol(ax, sym, dx, dy, layer_patches):
    for b in sym.boxes:
        color = _LAYER_COLORS.get(b.layer, _DEFAULT_COLOR)
        rect = mpatches.Rectangle(
            (b.cx - b.width // 2 + dx, b.cy - b.height // 2 + dy),
            b.width, b.height,
            linewidth=_LINE_WIDTH,
            edgecolor="black",
            facecolor=color,
            alpha=_ALPHA,
        )
        ax.add_patch(rect)
        _register_layer(layer_patches, b.layer, color)

    for p in sym.polygons:
        if len(p.points) >= 3:
            color = _LAYER_COLORS.get(p.layer, _DEFAULT_COLOR)
            xs = [pt[0] + dx for pt in p.points] + [p.points[0][0] + dx]
            ys = [pt[1] + dy for pt in p.points] + [p.points[0][1] + dy]
            ax.fill(xs, ys, color=color, alpha=_ALPHA, linewidth=0)
            ax.plot(xs, ys, color="black", linewidth=_LINE_WIDTH)
            _register_layer(layer_patches, p.layer, color)

    for w in sym.wires:
        if len(w.points) >= 2:
            color = _LAYER_COLORS.get(w.layer, _DEFAULT_COLOR)
            xs = [pt[0] + dx for pt in w.points]
            ys = [pt[1] + dy for pt in w.points]
            ax.plot(xs, ys, color=color, linewidth=w.width * 0.01 + _LINE_WIDTH)
            _register_layer(layer_patches, w.layer, color)


def _register_layer(patches, layer, color):
    if layer and layer not in patches:
        patches[layer] = mpatches.Patch(
            facecolor=color, edgecolor="black",
            linewidth=_LINE_WIDTH, alpha=_ALPHA, label=layer,
        )


def plot_before_after(
    layout_before: CIFLayout,
    layout_after:  CIFLayout,
    benchmark_name: str,
    out_path: str,
    dpi: int = 150,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor("white")
    plt.subplots_adjust(wspace=0.35, top=0.88)

    plot_layout(layout_before, title="Before compaction", ax=axes[0], show_legend=False)
    plot_layout(layout_after,  title="After compaction",  ax=axes[1], show_legend=True)

    fig.suptitle(
        f"Layout: {benchmark_name}",
        fontsize=_FONT_SIZE + 2,
        y=0.97,
    )
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Saved before/after snapshot: %s", out_path)
