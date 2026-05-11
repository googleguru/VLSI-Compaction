"""
CIF / Magic .mag layout renderer.

Draws geometry on white-background matplotlib figures using technology-aware
layer color palettes.  Supports:
  - Standard CIF layer visualization
  - Magic SCMOS / SkyWater sky130A / generic technology palettes
  - Before/after compaction snapshots (side-by-side)
  - Magic-style layout rendering with hatch patterns per layer type
"""

import os
import logging
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import Optional, Dict, List

from ..io.cif_reader import CIFLayout

logger = logging.getLogger(__name__)

# ── Technology-specific layer palettes ───────────────────────────────────────
# Keys match both uppercase CIF names and lowercase Magic names.

_SCMOS_COLORS: Dict[str, str] = {
    # Active / diffusion
    "NDIFF":        "#5BA4CF",   # blue-teal
    "PDIFF":        "#E8825E",   # salmon
    "DIFF":         "#5BA4CF",
    "NDIFFUSION":   "#5BA4CF",
    "PDIFFUSION":   "#E8825E",
    "NSD":          "#5BA4CF",
    "PSD":          "#E8825E",
    # Gate
    "POLY":         "#E63946",   # red
    # Well
    "NWELL":        "#B7E4C7",   # pale green
    "PWELL":        "#FFD6A5",   # pale orange
    # Contacts / vias
    "CONT":         "#264653",
    "CONTACT":      "#264653",
    "LICON":        "#264653",
    "VIA1":         "#6D6875",
    "VIA":          "#6D6875",
    "MCON":         "#6D6875",
    "VIA2":         "#9B5DE5",
    "VIA3":         "#C77DFF",
    # Metal layers
    "METAL1":       "#1D3557",   # dark blue
    "LI":           "#1D3557",
    "METAL2":       "#F4A261",   # orange
    "MET1":         "#F4A261",
    "METAL3":       "#2A9D8F",   # teal
    "MET2":         "#2A9D8F",
    "METAL4":       "#E9C46A",   # gold
    "MET3":         "#E9C46A",
    "METAL5":       "#A8DADC",   # light blue
    "MET4":         "#A8DADC",
}

_SKY130_COLORS: Dict[str, str] = {
    "NSD":          "#5BA4CF",
    "PSD":          "#E8825E",
    "POLY":         "#E63946",
    "NWELL":        "#B7E4C7",
    "PWELL":        "#FFD6A5",
    "LICON":        "#264653",
    "LI":           "#457B9D",
    "MCON":         "#6D6875",
    "MET1":         "#F4A261",
    "VIA":          "#9B5DE5",
    "MET2":         "#2A9D8F",
    "VIA2":         "#C77DFF",
    "MET3":         "#E9C46A",
    "VIA3":         "#FF6B6B",
    "MET4":         "#A8DADC",
    "VIA4":         "#06D6A0",
    "MET5":         "#118AB2",
}

# CIF uppercase aliases pointing into the scmos palette
_CIF_ALIASES: Dict[str, str] = {
    k.upper(): v for k, v in _SCMOS_COLORS.items()
}

_DEFAULT_COLOR = "#BBBBBB"

_PALETTES = {
    "scmos":    _SCMOS_COLORS,
    "sky130a":  _SKY130_COLORS,
    "sky130b":  _SKY130_COLORS,
    "default":  _CIF_ALIASES,
}

# Layer type → hatch pattern (Magic-style visual distinction)
_HATCH: Dict[str, str] = {
    "poly":     "",
    "ndiff":    "///",
    "pdiff":    "\\\\\\",
    "nwell":    "...",
    "pwell":    "xxx",
    "cont":     "++",
    "contact":  "++",
    "licon":    "++",
    "via1":     "**",
    "via":      "**",
    "metal1":   "",
    "metal2":   "",
    "metal3":   "",
    "li":       "",
    "met1":     "",
}

_FONT_SIZE  = 9
_LINE_WIDTH = 0.6
_ALPHA      = 0.70


def _color(layer: str, palette: Dict[str, str]) -> str:
    return (
        palette.get(layer.upper())
        or palette.get(layer.lower())
        or _DEFAULT_COLOR
    )


def _hatch(layer: str) -> str:
    return _HATCH.get(layer.lower(), "")


# ── Core drawing functions ────────────────────────────────────────────────────

def plot_layout(
    layout: CIFLayout,
    title: str = "",
    ax: Optional[plt.Axes] = None,
    show_legend: bool = True,
    tech: str = "scmos",
) -> plt.Axes:
    """
    Render a CIFLayout (or converted .mag layout) onto *ax*.

    Parameters
    ----------
    tech : str
        Color palette: 'scmos', 'sky130a', 'sky130b', or 'default'
    """
    palette = _palettes_for(tech)

    fig_created = ax is None
    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 5))
        fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    layer_patches: Dict[str, mpatches.Patch] = {}

    if layout.top_calls:
        for call in layout.top_calls:
            sym = layout.symbols.get(call.symbol_num)
            if sym:
                _draw_symbol(ax, sym, call.tx, call.ty, layer_patches, palette)
    else:
        for sym in layout.symbols.values():
            _draw_symbol(ax, sym, 0, 0, layer_patches, palette)

    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.tick_params(labelsize=_FONT_SIZE)
    ax.set_xlabel("X (units)", fontsize=_FONT_SIZE)
    ax.set_ylabel("Y (units)", fontsize=_FONT_SIZE)
    if title:
        ax.set_title(title, fontsize=_FONT_SIZE + 1, pad=4)

    if show_legend and layer_patches:
        handles = list(layer_patches.values())[:12]   # cap legend entries
        ax.legend(
            handles=handles,
            loc="upper right",
            fontsize=_FONT_SIZE - 1,
            framealpha=0.9,
            ncol=max(1, len(handles) // 6),
        )
    return ax


def plot_magic_layout(
    layout: CIFLayout,
    title: str = "",
    tech: str = "scmos",
    out_path: Optional[str] = None,
    dpi: int = 150,
) -> plt.Figure:
    """
    Render a layout with Magic-style technology coloring and hatch patterns.
    Saves to *out_path* if given; always returns the Figure.
    """
    palette = _palettes_for(tech)

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    layer_patches: Dict[str, mpatches.Patch] = {}

    if layout.top_calls:
        for call in layout.top_calls:
            sym = layout.symbols.get(call.symbol_num)
            if sym:
                _draw_symbol_magic(ax, sym, call.tx, call.ty, layer_patches, palette)
    else:
        for sym in layout.symbols.values():
            _draw_symbol_magic(ax, sym, 0, 0, layer_patches, palette)

    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.tick_params(labelsize=_FONT_SIZE)
    ax.set_xlabel("X (units)", fontsize=_FONT_SIZE)
    ax.set_ylabel("Y (units)", fontsize=_FONT_SIZE)
    title_str = title or f"Layout ({tech})"
    ax.set_title(title_str, fontsize=_FONT_SIZE + 1, pad=4)

    for sp in ax.spines.values():
        sp.set_linewidth(0.5)

    if layer_patches:
        handles = list(layer_patches.values())[:14]
        ax.legend(
            handles=handles,
            loc="upper right",
            fontsize=_FONT_SIZE - 1,
            framealpha=0.95,
            ncol=max(1, len(handles) // 7),
        )

    if out_path:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        fig.savefig(out_path, dpi=dpi, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        logger.info("Saved Magic-style layout: %s", out_path)

    return fig


def plot_before_after(
    layout_before: CIFLayout,
    layout_after:  CIFLayout,
    benchmark_name: str,
    out_path: str,
    dpi: int = 150,
    tech: str = "scmos",
) -> None:
    """Side-by-side before/after compaction snapshot."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor("white")
    plt.subplots_adjust(wspace=0.35, top=0.88)

    plot_layout(layout_before, "Before compaction",  ax=axes[0], show_legend=False, tech=tech)
    plot_layout(layout_after,  "After compaction",   ax=axes[1], show_legend=True,  tech=tech)

    fig.suptitle(f"Layout: {benchmark_name}  [{tech}]",
                 fontsize=_FONT_SIZE + 2, y=0.97)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Saved before/after snapshot: %s", out_path)


# ── private helpers ───────────────────────────────────────────────────────────

def _palettes_for(tech: str) -> Dict[str, str]:
    key = tech.lower().replace("-", "").replace("_", "")
    for k, v in _PALETTES.items():
        if key.startswith(k.replace("_", "")):
            return v
    return _CIF_ALIASES


def _draw_symbol(ax, sym, dx, dy, layer_patches, palette):
    for b in sym.boxes:
        clr = _color(b.layer, palette)
        ax.add_patch(mpatches.Rectangle(
            (b.cx - b.width // 2 + dx, b.cy - b.height // 2 + dy),
            b.width, b.height,
            linewidth=_LINE_WIDTH, edgecolor="black",
            facecolor=clr, alpha=_ALPHA,
        ))
        _reg(layer_patches, b.layer, clr, "")

    for p in sym.polygons:
        if len(p.points) >= 3:
            clr = _color(p.layer, palette)
            xs  = [pt[0] + dx for pt in p.points] + [p.points[0][0] + dx]
            ys  = [pt[1] + dy for pt in p.points] + [p.points[0][1] + dy]
            ax.fill(xs, ys, color=clr, alpha=_ALPHA, linewidth=0)
            ax.plot(xs, ys, color="black", linewidth=_LINE_WIDTH)
            _reg(layer_patches, p.layer, clr, "")

    for w in sym.wires:
        if len(w.points) >= 2:
            clr = _color(w.layer, palette)
            xs  = [pt[0] + dx for pt in w.points]
            ys  = [pt[1] + dy for pt in w.points]
            ax.plot(xs, ys, color=clr, linewidth=max(1, w.width * 0.002))
            _reg(layer_patches, w.layer, clr, "")


def _draw_symbol_magic(ax, sym, dx, dy, layer_patches, palette):
    """Magic-style rendering: hatch patterns + slightly thicker outlines."""
    for b in sym.boxes:
        clr = _color(b.layer, palette)
        ht  = _hatch(b.layer)
        ax.add_patch(mpatches.FancyBboxPatch(
            (b.cx - b.width // 2 + dx, b.cy - b.height // 2 + dy),
            b.width, b.height,
            boxstyle="square,pad=0",
            linewidth=0.8, edgecolor="black",
            facecolor=clr, alpha=_ALPHA,
            hatch=ht,
        ))
        _reg(layer_patches, b.layer, clr, ht)

    for p in sym.polygons:
        if len(p.points) >= 3:
            clr = _color(p.layer, palette)
            ht  = _hatch(p.layer)
            xs  = [pt[0] + dx for pt in p.points] + [p.points[0][0] + dx]
            ys  = [pt[1] + dy for pt in p.points] + [p.points[0][1] + dy]
            ax.fill(xs, ys, color=clr, alpha=_ALPHA, hatch=ht, linewidth=0)
            ax.plot(xs, ys, color="black", linewidth=0.8)
            _reg(layer_patches, p.layer, clr, ht)


def _reg(patches, layer, color, hatch):
    if layer and layer not in patches:
        patches[layer] = mpatches.Patch(
            facecolor=color, edgecolor="black",
            linewidth=_LINE_WIDTH, alpha=_ALPHA,
            hatch=hatch, label=layer,
        )
