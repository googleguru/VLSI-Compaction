"""
Bar and line charts for CA planning metrics, reduction results, and convergence.

Design rules
------------
- White background, no overlapping labels, publication-ready typography.
- Convergence curves always run the full epoch range (convergence_threshold=0)
  to guarantee a visible multi-point curve regardless of how fast the CA settles.
- Bar charts show CA planning metrics (shrink savings, epoch counts) when
  backend compaction results are unavailable (all zeros), so every chart
  contains visible, real data.
"""

import os
import logging
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_FONT      = 10
_LW        = 1.4
_MARKER_S  = 4
_COLORS    = ["#1D3557", "#E63946", "#F4A261", "#2A9D8F", "#457B9D", "#6D6875", "#E9C46A"]
_GRID_KW   = dict(linewidth=0.4, alpha=0.45, linestyle="--")


# ── helpers ───────────────────────────────────────────────────────────────────

def _setup_fig(w=7, h=4.5):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    for sp in ax.spines.values():
        sp.set_linewidth(0.7)
    return fig, ax


def _save(fig, path, dpi):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    logger.info("Saved: %s", path)


def _bar_group(ax, benchmarks, policies, values_map, colors, bar_width=0.8):
    """
    Draw a grouped-bar chart on `ax`.
    values_map: {policy: [val_per_benchmark]}
    """
    x = np.arange(len(benchmarks))
    n = max(len(policies), 1)
    w = bar_width / n
    for i, policy in enumerate(policies):
        offset = (i - n / 2 + 0.5) * w
        vals = values_map.get(policy, [0.0] * len(benchmarks))
        ax.bar(x + offset, vals, width=w * 0.88,
               color=colors[i % len(colors)],
               label=policy, linewidth=0.5, edgecolor="white")
    ax.set_xticks(x)
    ax.set_xticklabels(benchmarks, fontsize=_FONT - 1, rotation=15, ha="right")
    ax.tick_params(labelsize=_FONT - 1)
    ax.grid(axis="y", **_GRID_KW)
    ax.set_axisbelow(True)


# ── convergence curve  (primary figure) ─────────────────────────────────────

def convergence_curve_full(
    epoch_results,            # list of EpochResult objects
    benchmark_name: str,
    policy: str,
    out_path: str,
    dpi: int = 150,
) -> None:
    """
    Four-panel convergence figure:
      (a) X-pressure magnitude vs epoch
      (b) Y-pressure magnitude vs epoch
      (c) Active-cell fraction vs epoch  — shows stabilisation rule effect
      (d) Suggested shrink factors (Xshrf, Yshrf) vs epoch

    Uses ALL epochs regardless of early-stopping so the curves are always
    multi-point and visually complete.
    """
    if not epoch_results:
        logger.warning("No epoch results for %s/%s — skipping convergence figure",
                       benchmark_name, policy)
        return

    epochs   = [e.epoch for e in epoch_results]
    xp       = [e.aggregate_pressure.get("mean_xp", 0.0) for e in epoch_results]
    yp       = [e.aggregate_pressure.get("mean_yp", 0.0) for e in epoch_results]
    act      = [e.active_fraction for e in epoch_results]
    xshrf    = [e.suggested_xshrf for e in epoch_results]
    yshrf    = [e.suggested_yshrf for e in epoch_results]

    fig, axes = plt.subplots(2, 2, figsize=(11, 7))
    fig.patch.set_facecolor("white")
    fig.suptitle(
        f"CA Planning Convergence — {benchmark_name}  /  {policy}",
        fontsize=_FONT + 2, y=1.01,
    )

    panel_data = [
        (axes[0, 0], xp,    "Mean |X-pressure|",       _COLORS[0], "o"),
        (axes[0, 1], yp,    "Mean |Y-pressure|",       _COLORS[1], "s"),
        (axes[1, 0], act,   "Active Cell Fraction",    _COLORS[2], "^"),
        (axes[1, 1], None,  "Suggested Shrink Factors", None,       None),
    ]

    for ax, data, ylabel, color, marker in panel_data[:3]:
        ax.set_facecolor("white")
        ax.plot(epochs, data, color=color, linewidth=_LW,
                marker=marker, markersize=_MARKER_S)
        ax.set_xlabel("Epoch", fontsize=_FONT)
        ax.set_ylabel(ylabel, fontsize=_FONT)
        ax.set_title(ylabel, fontsize=_FONT, pad=4)
        ax.tick_params(labelsize=_FONT - 1)
        ax.grid(**_GRID_KW)
        ax.set_xlim(left=0)
        # Ensure y-range is never collapsed to a dot
        ymin, ymax = min(data), max(data)
        margin = max((ymax - ymin) * 0.12, 1e-4)
        ax.set_ylim(max(0, ymin - margin), ymax + margin)

    # Shrink factor panel
    ax4 = axes[1, 1]
    ax4.set_facecolor("white")
    ax4.plot(epochs, xshrf, color=_COLORS[3], linewidth=_LW,
             marker="o", markersize=_MARKER_S, label="Xshrf")
    ax4.plot(epochs, yshrf, color=_COLORS[4], linewidth=_LW,
             marker="s", markersize=_MARKER_S, label="Yshrf",
             linestyle="--")
    ax4.set_xlabel("Epoch", fontsize=_FONT)
    ax4.set_ylabel("Shrink Factor", fontsize=_FONT)
    ax4.set_title("Suggested Shrink Factors (Xshrf, Yshrf)", fontsize=_FONT, pad=4)
    ax4.legend(fontsize=_FONT - 1, framealpha=0.9)
    ax4.tick_params(labelsize=_FONT - 1)
    ax4.grid(**_GRID_KW)
    ax4.set_xlim(left=0)
    all_shrf = xshrf + yshrf
    ymin, ymax = min(all_shrf), max(all_shrf)
    margin = max((ymax - ymin) * 0.12, 5e-4)
    ax4.set_ylim(ymin - margin, ymax + margin)

    plt.tight_layout(pad=1.8)
    _save(fig, out_path, dpi)


def convergence_curve(
    pressure_history_x: List[float],
    pressure_history_y: List[float],
    benchmark_name: str,
    policy: str,
    out_path: str,
    dpi: int = 150,
) -> None:
    """
    Simple two-line convergence plot (kept for backwards compatibility).
    Call convergence_curve_full() instead for publication figures.
    """
    if not pressure_history_x:
        return
    fig, ax = _setup_fig(6, 4)
    epochs = list(range(len(pressure_history_x)))
    ax.plot(epochs, pressure_history_x, color=_COLORS[0], linewidth=_LW,
            marker="o", markersize=_MARKER_S, label="X-pressure (mean |xp|)")
    ax.plot(epochs, pressure_history_y, color=_COLORS[1], linewidth=_LW,
            marker="s", markersize=_MARKER_S, label="Y-pressure (mean |yp|)",
            linestyle="--")
    ax.set_xlabel("CA Epoch", fontsize=_FONT)
    ax.set_ylabel("Mean |Pressure|", fontsize=_FONT)
    ax.set_title(f"CA Convergence — {benchmark_name} / {policy}", fontsize=_FONT + 1)
    ax.legend(fontsize=_FONT - 1, framealpha=0.9)
    ax.tick_params(labelsize=_FONT - 1)
    ax.grid(**_GRID_KW)
    ax.set_xlim(left=0)
    # Guarantee non-collapsed y-axis
    ymin = min(min(pressure_history_x), min(pressure_history_y))
    ymax = max(max(pressure_history_x), max(pressure_history_y))
    margin = max((ymax - ymin) * 0.15, 1e-4)
    ax.set_ylim(max(0.0, ymin - margin), ymax + margin)
    _save(fig, out_path, dpi)


# ── CA planning bar charts  (visible without backend) ─────────────────────────

def ca_shrink_savings_bar(
    planning_results: List[dict],
    out_path: str,
    dpi: int = 150,
) -> None:
    """
    Grouped bar chart: CA-recommended shrink savings per policy per benchmark.

    Shrink saving = (1 - xshrf) * 100 [%] and (1 - yshrf) * 100 [%].
    These are real CA planning outputs, always non-zero when rules run.
    Clearly labelled as planning recommendations, not measured compaction.

    planning_results: list of dicts with keys:
        benchmark, policy, xshrf, yshrf
    """
    if not planning_results:
        return

    benchmarks = sorted(set(r["benchmark"] for r in planning_results))
    policies   = list(dict.fromkeys(r["policy"] for r in planning_results))

    x_savings = {
        p: [(1 - next(
                (r["xshrf"] for r in planning_results
                 if r["benchmark"] == bm and r["policy"] == p), 0.99
             )) * 100
            for bm in benchmarks]
        for p in policies
    }
    y_savings = {
        p: [(1 - next(
                (r["yshrf"] for r in planning_results
                 if r["benchmark"] == bm and r["policy"] == p), 0.99
             )) * 100
            for bm in benchmarks]
        for p in policies
    }

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor("white")
    fig.suptitle(
        "CA Planning: Recommended Shrink Savings per Policy\n"
        "(actual compaction results require the Perl backend)",
        fontsize=_FONT + 1, y=1.03,
    )

    for ax, savings, axis_label in [
        (axes[0], x_savings, "X-axis Shrink Saving  (1 − Xshrf) × 100  [%]"),
        (axes[1], y_savings, "Y-axis Shrink Saving  (1 − Yshrf) × 100  [%]"),
    ]:
        _bar_group(ax, benchmarks, policies, savings, _COLORS)
        ax.set_ylabel(axis_label, fontsize=_FONT)
        ymax = max(v for vals in savings.values() for v in vals)
        ax.set_ylim(0, max(ymax * 1.25, 0.5))
        ax.legend(fontsize=_FONT - 2, loc="upper right", framealpha=0.9)
        for sp in ax.spines.values():
            sp.set_linewidth(0.7)

    plt.tight_layout(pad=2.0)
    _save(fig, out_path, dpi)


def ca_epoch_profile_bar(
    planning_results: List[dict],
    out_path: str,
    dpi: int = 150,
) -> None:
    """
    Bar chart: CA epochs to convergence and final active-cell fraction per policy.

    planning_results: list of dicts with keys:
        benchmark, policy, ca_epochs, final_active_fraction
    """
    if not planning_results:
        return

    benchmarks = sorted(set(r["benchmark"] for r in planning_results))
    policies   = list(dict.fromkeys(r["policy"] for r in planning_results
                                    if r["policy"] != "backend_only"))

    epoch_map = {
        p: [next((r["ca_epochs"] for r in planning_results
                  if r["benchmark"] == bm and r["policy"] == p), 0)
            for bm in benchmarks]
        for p in policies
    }
    act_map = {
        p: [next((r.get("final_active_fraction", 1.0)
                  for r in planning_results
                  if r["benchmark"] == bm and r["policy"] == p), 1.0)
            for bm in benchmarks]
        for p in policies
    }

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor("white")
    fig.suptitle(
        "CA Planning: Epoch Count and Cell Stabilisation per Policy",
        fontsize=_FONT + 1, y=1.02,
    )

    _bar_group(axes[0], benchmarks, policies, epoch_map, _COLORS)
    axes[0].set_ylabel("Epochs to Convergence", fontsize=_FONT)
    axes[0].set_title("CA Epochs (forced-full run = max_epochs)", fontsize=_FONT, pad=4)
    axes[0].legend(fontsize=_FONT - 2, loc="upper right", framealpha=0.9)
    for sp in axes[0].spines.values(): sp.set_linewidth(0.7)

    _bar_group(axes[1], benchmarks, policies, act_map, _COLORS)
    axes[1].set_ylabel("Final Active-Cell Fraction", fontsize=_FONT)
    axes[1].set_title(
        "Fraction of geometry cells still eligible\nat final epoch (lower = more stabilised)",
        fontsize=_FONT, pad=4,
    )
    axes[1].set_ylim(0, 1.15)
    axes[1].legend(fontsize=_FONT - 2, loc="upper right", framealpha=0.9)
    for sp in axes[1].spines.values(): sp.set_linewidth(0.7)

    plt.tight_layout(pad=2.0)
    _save(fig, out_path, dpi)


def policy_comparison_lines(
    policy_epoch_data: Dict[str, Tuple[List[float], List[float]]],
    benchmark_name: str,
    out_path: str,
    dpi: int = 150,
) -> None:
    """
    Multi-policy X-pressure convergence overlay on a single axes.
    policy_epoch_data: {policy_name: (xp_list, yp_list)}
    """
    if not policy_epoch_data:
        return

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    fig.patch.set_facecolor("white")
    fig.suptitle(
        f"Policy Comparison — {benchmark_name}  (forced full-epoch run)",
        fontsize=_FONT + 1, y=1.02,
    )

    for ax, idx, label in [(axes[0], 0, "X-pressure"), (axes[1], 1, "Y-pressure")]:
        ax.set_facecolor("white")
        for i, (policy, (xp_h, yp_h)) in enumerate(policy_epoch_data.items()):
            data = xp_h if idx == 0 else yp_h
            if not data:
                continue
            epochs = list(range(len(data)))
            ax.plot(epochs, data, color=_COLORS[i % len(_COLORS)],
                    linewidth=_LW, marker=["o", "s", "^", "D", "v", "P", "X"][i % 7],
                    markersize=_MARKER_S, label=policy)
        ax.set_xlabel("Epoch", fontsize=_FONT)
        ax.set_ylabel(f"Mean |{label}|", fontsize=_FONT)
        ax.set_title(f"{label} Evolution", fontsize=_FONT, pad=4)
        ax.legend(fontsize=_FONT - 2, loc="upper right", framealpha=0.9,
                  ncol=max(1, len(policy_epoch_data) // 4))
        ax.tick_params(labelsize=_FONT - 1)
        ax.grid(**_GRID_KW)
        ax.set_xlim(left=0)
        all_vals = [v for _, (xp, yp) in policy_epoch_data.items()
                    for v in (xp if idx == 0 else yp)]
        if all_vals:
            ymin, ymax = min(all_vals), max(all_vals)
            margin = max((ymax - ymin) * 0.15, 1e-4)
            ax.set_ylim(max(0, ymin - margin), ymax + margin)
        for sp in ax.spines.values():
            sp.set_linewidth(0.7)

    plt.tight_layout(pad=2.0)
    _save(fig, out_path, dpi)


# ── backend-result charts (shown when backend available) ─────────────────────

def area_reduction_bar(
    metrics_list,
    out_path: str,
    dpi: int = 150,
    metric: str = "area_reduction_pct",
    ylabel: str = "Area Reduction (%)",
    title: str  = "Area Reduction by Policy",
) -> None:
    benchmarks = sorted(set(m.benchmark for m in metrics_list))
    policies   = list(dict.fromkeys(m.policy for m in metrics_list))

    values_map = {}
    for policy in policies:
        vals = []
        for bm in benchmarks:
            row = next((m for m in metrics_list
                        if m.benchmark == bm and m.policy == policy), None)
            vals.append(getattr(row, metric, 0.0)
                        if row and getattr(row, "backend_ok", False) else 0.0)
        values_map[policy] = vals

    fig, ax = _setup_fig(max(7, len(benchmarks) * 1.5 + 2), 4.5)
    _bar_group(ax, benchmarks, policies, values_map, _COLORS)
    ax.set_ylabel(ylabel,  fontsize=_FONT)
    ax.set_title(title,    fontsize=_FONT + 1, pad=6)
    ax.legend(fontsize=_FONT - 1, loc="upper right", framealpha=0.9)
    _save(fig, out_path, dpi)


def width_height_reduction_chart(metrics_list, out_path: str, dpi: int = 150) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    fig.patch.set_facecolor("white")
    for ax, metric, ylabel, title in [
        (axes[0], "width_reduction_pct",  "Width Reduction (%)",  "Width Reduction by Policy"),
        (axes[1], "height_reduction_pct", "Height Reduction (%)", "Height Reduction by Policy"),
    ]:
        benchmarks = sorted(set(m.benchmark for m in metrics_list))
        policies   = list(dict.fromkeys(m.policy for m in metrics_list))
        values_map = {
            p: [getattr(
                    next((m for m in metrics_list
                          if m.benchmark == bm and m.policy == p), None),
                    metric, 0.0) or 0.0
                for bm in benchmarks]
            for p in policies
        }
        _bar_group(ax, benchmarks, policies, values_map, _COLORS)
        ax.set_ylabel(ylabel, fontsize=_FONT)
        ax.set_title(title, fontsize=_FONT + 1, pad=4)
        ax.legend(fontsize=_FONT - 2, loc="upper right", framealpha=0.9)
        for sp in ax.spines.values(): sp.set_linewidth(0.7)
    plt.tight_layout(pad=2.0)
    _save(fig, out_path, dpi)


def ablation_comparison_chart(metrics_list, out_path: str, dpi: int = 150) -> None:
    area_reduction_bar(
        metrics_list, out_path=out_path, dpi=dpi,
        metric="area_reduction_pct",
        ylabel="Area Reduction (%)",
        title="Ablation Study: Area Reduction by CA Policy",
    )
