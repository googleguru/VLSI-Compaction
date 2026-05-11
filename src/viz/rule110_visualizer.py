"""
Rule-110 CA visualizations.

Produces publication-ready figures from Rule110RunResult objects:
  - State evolution (multi-panel grid across epochs)
  - Pressure map evolution (fused 2-D field at selected epochs)
  - Shrink trajectory (X/Y shrink factors over all epochs)
  - Activity fraction curve (how active the CA is over time)
  - Policy matrix (pressure maps for all modes side-by-side)
"""

import os
import logging
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap
from typing import Dict, List, Optional

from ..ca.rule110_scheduler import Rule110Scheduler, Rule110RunResult

logger = logging.getLogger(__name__)

_FONT_SIZE  = 9
_TITLE_SIZE = 10
_DPI_DEFAULT = 150

# Custom colormaps
_CMAP_STATE    = LinearSegmentedColormap.from_list("state",    ["#FFFFFF", "#1D3557"])
_CMAP_PRESSURE = LinearSegmentedColormap.from_list("pressure", ["#FFFFFF", "#E63946", "#264653"])
_POLICY_COLORS = ["#1D3557", "#E63946", "#2A9D8F", "#E9C46A", "#6D6875"]


def _save(fig: plt.Figure, path: str, dpi: int = _DPI_DEFAULT) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Saved: %s", path)


def _run_r110(grid: np.ndarray, max_epochs: int = 20, mode: str = "alternating",
              damping: float = 0.85, boundary: str = "clamped") -> Rule110RunResult:
    sched = Rule110Scheduler(
        max_epochs=max_epochs,
        mode=mode,
        damping=damping,
        boundary=boundary,
    )
    return sched.run(grid)


# ── 1. State evolution ────────────────────────────────────────────────────────

def plot_state_evolution(
    run_result: Rule110RunResult,
    benchmark_name: str,
    out_path: str,
    dpi: int = _DPI_DEFAULT,
    n_panels: int = 6,
) -> None:
    """
    Multi-panel grid showing CA state snapshots at evenly-spaced epochs.
    Columns = selected epochs; top row = state heatmap, bottom row = pressure map.
    """
    epochs = run_result.epoch_results
    if not epochs:
        logger.warning("No epoch results for %s — skipping evolution figure", benchmark_name)
        return

    # Pick n_panels evenly-spaced epochs
    indices = np.linspace(0, len(epochs) - 1, min(n_panels, len(epochs)), dtype=int)
    selected = [epochs[i] for i in indices]
    n = len(selected)

    fig, axes = plt.subplots(2, n, figsize=(2.5 * n, 5))
    fig.patch.set_facecolor("white")
    fig.suptitle(
        f"Rule-110 State Evolution — {benchmark_name}",
        fontsize=_TITLE_SIZE, y=1.01,
    )

    for col, er in enumerate(selected):
        ax_s = axes[0, col] if n > 1 else axes[0]
        ax_p = axes[1, col] if n > 1 else axes[1]

        ax_s.imshow(er.state, cmap=_CMAP_STATE, vmin=0, vmax=1,
                    aspect="auto", interpolation="nearest")
        ax_s.set_title(f"Epoch {er.epoch}", fontsize=_FONT_SIZE)
        ax_s.set_xticks([])
        ax_s.set_yticks([])
        if col == 0:
            ax_s.set_ylabel("CA State", fontsize=_FONT_SIZE)

        im = ax_p.imshow(er.pressure_map, cmap=_CMAP_PRESSURE, vmin=0, vmax=1,
                         aspect="auto", interpolation="nearest")
        ax_p.set_xticks([])
        ax_p.set_yticks([])
        if col == 0:
            ax_p.set_ylabel("Pressure", fontsize=_FONT_SIZE)

    fig.colorbar(im, ax=axes[1, -1] if n > 1 else axes[1], fraction=0.046, pad=0.04,
                 label="Pressure", shrink=0.8)
    plt.tight_layout()
    _save(fig, out_path, dpi)


# ── 2. Shrink trajectory ──────────────────────────────────────────────────────

def plot_shrink_trajectory(
    run_result: Rule110RunResult,
    benchmark_name: str,
    out_path: str,
    dpi: int = _DPI_DEFAULT,
) -> None:
    """Line chart of X and Y shrink factors over all epochs."""
    xs, ys = run_result.shrink_history()
    if not xs:
        return
    epochs = list(range(len(xs)))

    fig, ax = plt.subplots(figsize=(6, 3.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.plot(epochs, xs, "-o", color="#E63946", linewidth=1.8, markersize=4, label="X shrink factor")
    ax.plot(epochs, ys, "-s", color="#1D3557", linewidth=1.8, markersize=4, label="Y shrink factor")

    ax.set_xlabel("Epoch", fontsize=_FONT_SIZE)
    ax.set_ylabel("Shrink factor", fontsize=_FONT_SIZE)
    ax.set_title(f"Rule-110 Shrink Trajectory — {benchmark_name}", fontsize=_TITLE_SIZE)
    ax.legend(fontsize=_FONT_SIZE)
    ax.set_ylim(0.75, 1.02)
    ax.axhline(y=1.0, color="#BBBBBB", linewidth=0.8, linestyle="--")
    ax.grid(axis="y", color="#EEEEEE", linewidth=0.8)
    ax.tick_params(labelsize=_FONT_SIZE)
    for sp in ax.spines.values():
        sp.set_linewidth(0.5)

    plt.tight_layout()
    _save(fig, out_path, dpi)


# ── 3. Activity fraction curve ────────────────────────────────────────────────

def plot_activity_curve(
    run_result: Rule110RunResult,
    benchmark_name: str,
    out_path: str,
    dpi: int = _DPI_DEFAULT,
) -> None:
    """Line chart of active cell fraction (CA density) over epochs."""
    if not run_result.epoch_results:
        return
    activity = [er.active_fraction for er in run_result.epoch_results]
    epochs   = list(range(len(activity)))

    fig, ax = plt.subplots(figsize=(6, 3.5))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    ax.fill_between(epochs, activity, alpha=0.15, color="#2A9D8F")
    ax.plot(epochs, activity, "-o", color="#2A9D8F", linewidth=1.8, markersize=4)

    ax.set_xlabel("Epoch", fontsize=_FONT_SIZE)
    ax.set_ylabel("Active cell fraction", fontsize=_FONT_SIZE)
    ax.set_title(f"Rule-110 Activity Fraction — {benchmark_name}", fontsize=_TITLE_SIZE)
    ax.set_ylim(0, 1.05)
    ax.grid(axis="y", color="#EEEEEE", linewidth=0.8)
    ax.tick_params(labelsize=_FONT_SIZE)
    for sp in ax.spines.values():
        sp.set_linewidth(0.5)

    plt.tight_layout()
    _save(fig, out_path, dpi)


# ── 4. Pressure evolution strip ───────────────────────────────────────────────

def plot_pressure_evolution(
    run_result: Rule110RunResult,
    benchmark_name: str,
    out_path: str,
    dpi: int = _DPI_DEFAULT,
    n_panels: int = 5,
) -> None:
    """Row of pressure map snapshots at selected epochs."""
    epochs = run_result.epoch_results
    if not epochs:
        return

    indices  = np.linspace(0, len(epochs) - 1, min(n_panels, len(epochs)), dtype=int)
    selected = [epochs[i] for i in indices]
    n = len(selected)

    fig, axes = plt.subplots(1, n, figsize=(2.8 * n, 3.2))
    fig.patch.set_facecolor("white")
    fig.suptitle(
        f"Rule-110 Pressure Evolution — {benchmark_name}",
        fontsize=_TITLE_SIZE,
    )

    for col, er in enumerate(selected):
        ax = axes[col] if n > 1 else axes
        im = ax.imshow(er.pressure_map, cmap=_CMAP_PRESSURE, vmin=0, vmax=1,
                       aspect="auto", interpolation="nearest")
        ax.set_title(f"Epoch {er.epoch}", fontsize=_FONT_SIZE)
        ax.set_xticks([])
        ax.set_yticks([])

    fig.colorbar(im, ax=axes[-1] if n > 1 else axes, fraction=0.046, pad=0.04,
                 label="Pressure", shrink=0.8)
    plt.tight_layout()
    _save(fig, out_path, dpi)


# ── 5. Policy matrix ──────────────────────────────────────────────────────────

_R110_MODES = [
    ("alternating",         "Alternating"),
    ("row_only",            "Row only"),
    ("col_only",            "Col only"),
]

_R110_BOUNDARIES = [
    ("clamped",   "Clamped"),
    ("periodic",  "Periodic"),
]


def plot_policy_matrix(
    grid: np.ndarray,
    benchmark_name: str,
    out_path: str,
    dpi: int = _DPI_DEFAULT,
    max_epochs: int = 20,
) -> None:
    """
    3×2 grid: rows = mode (alternating, row_only, col_only),
              cols = boundary (clamped, periodic).
    Each cell shows the final pressure map.
    """
    rows = _R110_MODES
    cols = _R110_BOUNDARIES
    nrow, ncol = len(rows), len(cols)

    fig, axes = plt.subplots(nrow, ncol, figsize=(ncol * 3.2, nrow * 3.0))
    fig.patch.set_facecolor("white")
    fig.suptitle(
        f"Rule-110 Policy Matrix — {benchmark_name}",
        fontsize=_TITLE_SIZE + 1, y=1.01,
    )

    for r, (mode, mode_label) in enumerate(rows):
        for c, (boundary, bound_label) in enumerate(cols):
            ax = axes[r, c]
            try:
                result = _run_r110(grid, max_epochs=max_epochs,
                                   mode=mode, boundary=boundary)
                pmap = result.final_pressure_map
                if pmap is None:
                    pmap = np.zeros_like(grid, dtype=float)
                im = ax.imshow(pmap, cmap=_CMAP_PRESSURE, vmin=0, vmax=1,
                               aspect="auto", interpolation="nearest")
            except Exception as exc:
                logger.warning("policy_matrix %s/%s failed: %s", mode, boundary, exc)
                ax.text(0.5, 0.5, "error", ha="center", va="center",
                        transform=ax.transAxes, fontsize=_FONT_SIZE)

            if r == 0:
                ax.set_title(bound_label, fontsize=_FONT_SIZE)
            if c == 0:
                ax.set_ylabel(mode_label, fontsize=_FONT_SIZE)
            ax.set_xticks([])
            ax.set_yticks([])

    fig.colorbar(im, ax=axes[:, -1].ravel().tolist(), fraction=0.03, pad=0.04,
                 label="Pressure")
    plt.tight_layout()
    _save(fig, out_path, dpi)


# ── 6. Shrink comparison across modes ────────────────────────────────────────

def plot_shrink_comparison(
    grid: np.ndarray,
    benchmark_name: str,
    out_path: str,
    dpi: int = _DPI_DEFAULT,
    max_epochs: int = 20,
) -> None:
    """
    Two subplots side-by-side: X shrink trajectory and Y shrink trajectory
    for all three modes (alternating / row_only / col_only), clamped boundary.
    """
    fig, (ax_x, ax_y) = plt.subplots(1, 2, figsize=(11, 4))
    fig.patch.set_facecolor("white")
    fig.suptitle(
        f"Rule-110 Shrink Comparison — {benchmark_name}",
        fontsize=_TITLE_SIZE + 1,
    )

    for idx, (mode, label) in enumerate(_R110_MODES):
        color = _POLICY_COLORS[idx]
        try:
            result = _run_r110(grid, max_epochs=max_epochs, mode=mode)
            xs, ys = result.shrink_history()
            epochs = list(range(len(xs)))
            ax_x.plot(epochs, xs, "-o", color=color, linewidth=1.6,
                      markersize=3.5, label=label)
            ax_y.plot(epochs, ys, "-s", color=color, linewidth=1.6,
                      markersize=3.5, label=label)
        except Exception as exc:
            logger.warning("shrink_comparison %s failed: %s", mode, exc)

    for ax, axis_label in [(ax_x, "X shrink factor"), (ax_y, "Y shrink factor")]:
        ax.set_xlabel("Epoch", fontsize=_FONT_SIZE)
        ax.set_ylabel(axis_label, fontsize=_FONT_SIZE)
        ax.set_ylim(0.75, 1.02)
        ax.axhline(y=1.0, color="#BBBBBB", linewidth=0.8, linestyle="--")
        ax.grid(axis="y", color="#EEEEEE", linewidth=0.8)
        ax.legend(fontsize=_FONT_SIZE - 1)
        ax.tick_params(labelsize=_FONT_SIZE)
        ax.set_facecolor("white")
        for sp in ax.spines.values():
            sp.set_linewidth(0.5)

    plt.tight_layout()
    _save(fig, out_path, dpi)


# ── 7. Column/row pressure bar profiles ──────────────────────────────────────

def plot_pressure_profiles(
    run_result: Rule110RunResult,
    benchmark_name: str,
    out_path: str,
    dpi: int = _DPI_DEFAULT,
) -> None:
    """
    Final epoch column pressure (bar) and row pressure (bar) side-by-side.
    Shows spatial pressure distribution across layout columns and rows.
    """
    if not run_result.epoch_results:
        return
    last = run_result.epoch_results[-1]
    col_p = last.col_pressure
    row_p = last.row_pressure

    fig, (ax_c, ax_r) = plt.subplots(1, 2, figsize=(11, 3.8))
    fig.patch.set_facecolor("white")
    fig.suptitle(
        f"Rule-110 Final Pressure Profiles — {benchmark_name}",
        fontsize=_TITLE_SIZE + 1,
    )

    colors_c = plt.cm.RdYlGn_r(col_p / max(col_p.max(), 1e-6))
    colors_r = plt.cm.RdYlGn_r(row_p / max(row_p.max(), 1e-6))

    ax_c.bar(range(len(col_p)), col_p, color=colors_c, edgecolor="none", width=1.0)
    ax_c.set_xlabel("Column index", fontsize=_FONT_SIZE)
    ax_c.set_ylabel("Mean activity", fontsize=_FONT_SIZE)
    ax_c.set_title("Column pressure (X axis)", fontsize=_FONT_SIZE)
    ax_c.set_ylim(0, 1.05)
    ax_c.grid(axis="y", color="#EEEEEE", linewidth=0.8)
    ax_c.tick_params(labelsize=_FONT_SIZE)
    ax_c.set_facecolor("white")

    ax_r.barh(range(len(row_p)), row_p, color=colors_r, edgecolor="none", height=1.0)
    ax_r.set_xlabel("Mean activity", fontsize=_FONT_SIZE)
    ax_r.set_ylabel("Row index", fontsize=_FONT_SIZE)
    ax_r.set_title("Row pressure (Y axis)", fontsize=_FONT_SIZE)
    ax_r.set_xlim(0, 1.05)
    ax_r.grid(axis="x", color="#EEEEEE", linewidth=0.8)
    ax_r.invert_yaxis()
    ax_r.tick_params(labelsize=_FONT_SIZE)
    ax_r.set_facecolor("white")

    for ax in (ax_c, ax_r):
        for sp in ax.spines.values():
            sp.set_linewidth(0.5)

    plt.tight_layout()
    _save(fig, out_path, dpi)


# ── 8. Combined Rule-110 summary dashboard ───────────────────────────────────

def plot_r110_dashboard(
    run_result: Rule110RunResult,
    grid: np.ndarray,
    benchmark_name: str,
    out_path: str,
    dpi: int = _DPI_DEFAULT,
) -> None:
    """
    Single-page 2×3 dashboard:
      [0,0] Initial occupancy  [0,1] Final CA state   [0,2] Final pressure map
      [1,0] Shrink trajectory  [1,1] Activity curve   [1,2] Pressure profiles (col)
    """
    if not run_result.epoch_results:
        return
    last = run_result.epoch_results[-1]
    xs, ys = run_result.shrink_history()
    activity = [er.active_fraction for er in run_result.epoch_results]
    epochs = list(range(len(activity)))

    fig = plt.figure(figsize=(14, 8))
    fig.patch.set_facecolor("white")
    fig.suptitle(
        f"Rule-110 CA Dashboard — {benchmark_name}",
        fontsize=_TITLE_SIZE + 2, y=0.99,
    )
    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.42, wspace=0.35)

    # [0,0] Initial occupancy
    ax00 = fig.add_subplot(gs[0, 0])
    ax00.imshow(grid, cmap=_CMAP_STATE, vmin=0, vmax=1,
                aspect="auto", interpolation="nearest")
    ax00.set_title("Initial occupancy", fontsize=_FONT_SIZE)
    ax00.set_xticks([]); ax00.set_yticks([])

    # [0,1] Final CA state
    ax01 = fig.add_subplot(gs[0, 1])
    ax01.imshow(last.state, cmap=_CMAP_STATE, vmin=0, vmax=1,
                aspect="auto", interpolation="nearest")
    ax01.set_title(f"CA state (epoch {last.epoch})", fontsize=_FONT_SIZE)
    ax01.set_xticks([]); ax01.set_yticks([])

    # [0,2] Final pressure map
    ax02 = fig.add_subplot(gs[0, 2])
    im = ax02.imshow(last.pressure_map, cmap=_CMAP_PRESSURE, vmin=0, vmax=1,
                     aspect="auto", interpolation="nearest")
    ax02.set_title("Pressure map", fontsize=_FONT_SIZE)
    ax02.set_xticks([]); ax02.set_yticks([])
    fig.colorbar(im, ax=ax02, fraction=0.046, pad=0.04, shrink=0.85)

    # [1,0] Shrink trajectory
    ax10 = fig.add_subplot(gs[1, 0])
    ax10.set_facecolor("white")
    ax10.plot(epochs, xs, "-o", color="#E63946", linewidth=1.6, markersize=3, label="X")
    ax10.plot(epochs, ys, "-s", color="#1D3557", linewidth=1.6, markersize=3, label="Y")
    ax10.set_xlabel("Epoch", fontsize=_FONT_SIZE)
    ax10.set_ylabel("Shrink factor", fontsize=_FONT_SIZE)
    ax10.set_title("Shrink trajectory", fontsize=_FONT_SIZE)
    ax10.set_ylim(0.75, 1.02)
    ax10.legend(fontsize=_FONT_SIZE - 1)
    ax10.grid(axis="y", color="#EEEEEE", linewidth=0.8)
    ax10.tick_params(labelsize=_FONT_SIZE)
    for sp in ax10.spines.values():
        sp.set_linewidth(0.5)

    # [1,1] Activity curve
    ax11 = fig.add_subplot(gs[1, 1])
    ax11.set_facecolor("white")
    ax11.fill_between(epochs, activity, alpha=0.15, color="#2A9D8F")
    ax11.plot(epochs, activity, "-o", color="#2A9D8F", linewidth=1.6, markersize=3)
    ax11.set_xlabel("Epoch", fontsize=_FONT_SIZE)
    ax11.set_ylabel("Active fraction", fontsize=_FONT_SIZE)
    ax11.set_title("CA activity", fontsize=_FONT_SIZE)
    ax11.set_ylim(0, 1.05)
    ax11.grid(axis="y", color="#EEEEEE", linewidth=0.8)
    ax11.tick_params(labelsize=_FONT_SIZE)
    for sp in ax11.spines.values():
        sp.set_linewidth(0.5)

    # [1,2] Column pressure bar
    ax12 = fig.add_subplot(gs[1, 2])
    ax12.set_facecolor("white")
    col_p  = last.col_pressure
    colors = plt.cm.RdYlGn_r(col_p / max(col_p.max(), 1e-6))
    ax12.bar(range(len(col_p)), col_p, color=colors, edgecolor="none", width=1.0)
    ax12.set_xlabel("Column", fontsize=_FONT_SIZE)
    ax12.set_ylabel("Activity", fontsize=_FONT_SIZE)
    ax12.set_title("Column pressure", fontsize=_FONT_SIZE)
    ax12.set_ylim(0, 1.05)
    ax12.grid(axis="y", color="#EEEEEE", linewidth=0.8)
    ax12.tick_params(labelsize=_FONT_SIZE)
    for sp in ax12.spines.values():
        sp.set_linewidth(0.5)

    _save(fig, out_path, dpi)
