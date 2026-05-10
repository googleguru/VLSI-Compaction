"""
Bar and line charts for area/width/height reduction and convergence curves.
All figures use white backgrounds and publication-ready typography.
"""

import os
import logging
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple, Optional
from dataclasses import asdict

logger = logging.getLogger(__name__)

_FONT_SIZE  = 10
_LINE_WIDTH = 1.2
_COLORS     = ["#1D3557", "#457B9D", "#A8DADC", "#E63946", "#F4A261", "#2A9D8F", "#E9C46A"]


def _fig(w=7, h=4.5):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    for spine in ax.spines.values():
        spine.set_linewidth(0.7)
    return fig, ax


def area_reduction_bar(
    metrics_list,
    out_path: str,
    dpi: int = 150,
    metric: str = "area_reduction_pct",
    ylabel: str = "Area Reduction (%)",
    title: str  = "Area Reduction by Policy",
) -> None:
    from itertools import groupby

    benchmarks = sorted(set(m.benchmark for m in metrics_list))
    policies   = list(dict.fromkeys(m.policy for m in metrics_list))  # preserve order

    x   = np.arange(len(benchmarks))
    w   = 0.8 / max(len(policies), 1)

    fig, ax = _fig(max(7, len(benchmarks) * 1.5 + 2), 4.5)

    for i, policy in enumerate(policies):
        vals = []
        for bm in benchmarks:
            row = next(
                (m for m in metrics_list if m.benchmark == bm and m.policy == policy),
                None,
            )
            vals.append(getattr(row, metric, 0.0) if row and row.backend_ok else 0.0)
        offset = (i - len(policies) / 2 + 0.5) * w
        bars = ax.bar(
            x + offset, vals, width=w * 0.9,
            color=_COLORS[i % len(_COLORS)],
            label=policy, linewidth=0.5, edgecolor="white",
        )

    ax.set_xticks(x)
    ax.set_xticklabels(benchmarks, fontsize=_FONT_SIZE - 1, rotation=15, ha="right")
    ax.set_ylabel(ylabel,  fontsize=_FONT_SIZE)
    ax.set_title(title,    fontsize=_FONT_SIZE + 1, pad=6)
    ax.legend(fontsize=_FONT_SIZE - 1, loc="upper right", framealpha=0.9)
    ax.tick_params(labelsize=_FONT_SIZE - 1)
    ax.grid(axis="y", linewidth=0.4, alpha=0.5)
    ax.set_axisbelow(True)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Saved bar chart: %s", out_path)


def width_height_reduction_chart(
    metrics_list,
    out_path: str,
    dpi: int = 150,
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    fig.patch.set_facecolor("white")

    _bar_subplot(axes[0], metrics_list, "width_reduction_pct",
                 "Width Reduction (%)", "Width Reduction by Policy")
    _bar_subplot(axes[1], metrics_list, "height_reduction_pct",
                 "Height Reduction (%)", "Height Reduction by Policy")

    plt.tight_layout(pad=2.0)
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Saved width/height chart: %s", out_path)


def _bar_subplot(ax, metrics_list, metric, ylabel, title):
    benchmarks = sorted(set(m.benchmark for m in metrics_list))
    policies   = list(dict.fromkeys(m.policy for m in metrics_list))
    x = np.arange(len(benchmarks))
    w = 0.8 / max(len(policies), 1)

    ax.set_facecolor("white")
    for i, policy in enumerate(policies):
        vals = [
            getattr(
                next((m for m in metrics_list if m.benchmark == bm and m.policy == policy), None),
                metric, 0.0,
            ) or 0.0
            for bm in benchmarks
        ]
        offset = (i - len(policies) / 2 + 0.5) * w
        ax.bar(x + offset, vals, width=w * 0.9,
               color=_COLORS[i % len(_COLORS)], label=policy,
               linewidth=0.5, edgecolor="white")

    ax.set_xticks(x)
    ax.set_xticklabels(benchmarks, fontsize=_FONT_SIZE - 1, rotation=15, ha="right")
    ax.set_ylabel(ylabel, fontsize=_FONT_SIZE)
    ax.set_title(title, fontsize=_FONT_SIZE + 1, pad=4)
    ax.legend(fontsize=_FONT_SIZE - 2, loc="upper right", framealpha=0.9)
    ax.tick_params(labelsize=_FONT_SIZE - 1)
    ax.grid(axis="y", linewidth=0.4, alpha=0.5)
    ax.set_axisbelow(True)


def convergence_curve(
    pressure_history_x: List[float],
    pressure_history_y: List[float],
    benchmark_name: str,
    policy: str,
    out_path: str,
    dpi: int = 150,
) -> None:
    fig, ax = _fig(6, 4)

    epochs = list(range(len(pressure_history_x)))
    ax.plot(epochs, pressure_history_x, color=_COLORS[0], linewidth=_LINE_WIDTH,
            marker="o", markersize=3, label="X-pressure (mean |xp|)")
    ax.plot(epochs, pressure_history_y, color=_COLORS[3], linewidth=_LINE_WIDTH,
            marker="s", markersize=3, label="Y-pressure (mean |yp|)")

    ax.set_xlabel("CA Epoch", fontsize=_FONT_SIZE)
    ax.set_ylabel("Mean |Pressure|", fontsize=_FONT_SIZE)
    ax.set_title(f"CA Convergence: {benchmark_name} / {policy}", fontsize=_FONT_SIZE + 1)
    ax.legend(fontsize=_FONT_SIZE - 1, framealpha=0.9)
    ax.tick_params(labelsize=_FONT_SIZE - 1)
    ax.grid(linewidth=0.4, alpha=0.5)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Saved convergence curve: %s", out_path)


def ablation_comparison_chart(
    metrics_list,
    out_path: str,
    dpi: int = 150,
) -> None:
    area_reduction_bar(
        metrics_list,
        out_path=out_path,
        dpi=dpi,
        metric="area_reduction_pct",
        ylabel="Area Reduction (%)",
        title="Ablation Study: Area Reduction by CA Policy",
    )
