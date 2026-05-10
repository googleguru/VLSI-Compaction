"""
Heatmap visualizations for CA pressure fields and layout congestion.
"""

import os
import logging
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

logger = logging.getLogger(__name__)

_FONT_SIZE = 9


def _save_fig(fig, path, dpi):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Saved heatmap: %s", path)


def plot_pressure_heatmap(
    state: np.ndarray,
    benchmark_name: str,
    epoch: int,
    out_path: str,
    dpi: int = 150,
) -> None:
    """Plot X-pressure and Y-pressure side by side."""
    from ..ca.state_encoder import F_XPRESSURE, F_YPRESSURE
    xp = state[:, :, F_XPRESSURE]
    yp = state[:, :, F_YPRESSURE]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    fig.patch.set_facecolor("white")

    for ax, data, label in [
        (axes[0], xp, "X-Pressure"),
        (axes[1], yp, "Y-Pressure"),
    ]:
        vmax = max(float(np.abs(data).max()), 1e-6)
        norm = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)
        im = ax.imshow(
            data, origin="lower", cmap="RdBu_r", norm=norm,
            interpolation="nearest", aspect="auto",
        )
        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        ax.set_title(f"{label} — epoch {epoch}", fontsize=_FONT_SIZE + 1)
        ax.set_xlabel("Grid col", fontsize=_FONT_SIZE)
        ax.set_ylabel("Grid row", fontsize=_FONT_SIZE)
        ax.tick_params(labelsize=_FONT_SIZE - 1)

    fig.suptitle(f"{benchmark_name} CA Pressure Field", fontsize=_FONT_SIZE + 2, y=1.02)
    plt.tight_layout()
    _save_fig(fig, out_path, dpi)


def plot_occupancy_heatmap(
    grid: np.ndarray,
    benchmark_name: str,
    out_path: str,
    dpi: int = 150,
) -> None:
    """Plot binary occupancy grid."""
    fig, ax = plt.subplots(figsize=(6, 5))
    fig.patch.set_facecolor("white")

    cmap = matplotlib.colors.ListedColormap(
        ["white", "#1D3557", "#E63946", "#AAAAAA"]
    )
    ax.imshow(
        grid, origin="lower", cmap=cmap, vmin=0, vmax=3,
        interpolation="nearest", aspect="auto",
    )
    ax.set_title(f"{benchmark_name} Occupancy Grid", fontsize=_FONT_SIZE + 1)
    ax.set_xlabel("Grid col", fontsize=_FONT_SIZE)
    ax.set_ylabel("Grid row", fontsize=_FONT_SIZE)
    ax.tick_params(labelsize=_FONT_SIZE - 1)

    legend_elements = [
        matplotlib.patches.Patch(facecolor="white",   edgecolor="black", label="Empty"),
        matplotlib.patches.Patch(facecolor="#1D3557", label="Occupied"),
        matplotlib.patches.Patch(facecolor="#E63946", label="Keepout"),
        matplotlib.patches.Patch(facecolor="#AAAAAA", label="Boundary"),
    ]
    ax.legend(handles=legend_elements, loc="upper right",
              fontsize=_FONT_SIZE - 1, framealpha=0.9)

    _save_fig(fig, out_path, dpi)


def plot_congestion_heatmap(
    density: np.ndarray,
    benchmark_name: str,
    out_path: str,
    dpi: int = 150,
) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    fig.patch.set_facecolor("white")

    im = ax.imshow(density, origin="lower", cmap="YlOrRd",
                   vmin=0, vmax=1, interpolation="nearest", aspect="auto")
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="Density")
    ax.set_title(f"{benchmark_name} Congestion Map", fontsize=_FONT_SIZE + 1)
    ax.set_xlabel("Grid col", fontsize=_FONT_SIZE)
    ax.set_ylabel("Grid row", fontsize=_FONT_SIZE)
    ax.tick_params(labelsize=_FONT_SIZE - 1)

    _save_fig(fig, out_path, dpi)
