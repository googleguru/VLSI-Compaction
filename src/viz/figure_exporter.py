"""
Publication-ready figure exporter.
Reads evaluation results and CA run data to produce all required figures.

Convergence runs always use convergence_threshold=0.0 and max_epochs=20 so
every figure shows a full multi-point curve rather than a single dot.
"""

import os
import csv
import glob
import logging
import argparse
import yaml
import numpy as np
from typing import List, Dict, Tuple

from ..io.cif_reader import CIFReader
from ..ca.grid_discretizer import GridDiscretizer
from ..ca.composite_rules import load_ca_config, build_scheduler, all_policy_names
from ..ca.rule110_scheduler import Rule110Scheduler
from .layout_plotter import plot_before_after, plot_layout, plot_magic_layout
from .chart_generator import (
    area_reduction_bar,
    width_height_reduction_chart,
    ablation_comparison_chart,
    convergence_curve_full,
    ca_shrink_savings_bar,
    ca_epoch_profile_bar,
    policy_comparison_lines,
)
from .rule110_visualizer import (
    plot_state_evolution,
    plot_shrink_trajectory,
    plot_activity_curve,
    plot_pressure_evolution,
    plot_policy_matrix,
    plot_shrink_comparison,
    plot_pressure_profiles,
    plot_r110_dashboard,
)
from .heatmap_plotter import (
    plot_occupancy_heatmap,
    plot_pressure_heatmap,
    plot_congestion_heatmap,
)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

# Policies used for per-benchmark convergence and planning charts.
# Subset of all ablation policies chosen for readability.
_VIZ_POLICIES = [
    "full_composite",
    "simple_directional",
    "free_space_repulsion",
    "adaptive_shrink",
    "vonneumann_composite",
]


def _load_metrics_from_csv(csv_path: str) -> list:
    """Load metrics rows from a CSV file as simple namespace objects."""
    from types import SimpleNamespace
    if not os.path.isfile(csv_path):
        return []
    metrics = []
    with open(csv_path) as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            ns = SimpleNamespace(**{
                k: _coerce(k, v) for k, v in row.items()
            })
            metrics.append(ns)
    return metrics


_FLOAT_FIELDS = {
    "area_reduction_pct", "width_reduction_pct", "height_reduction_pct",
    "runtime_seconds", "xshrf", "yshrf",
}
_INT_FIELDS = {
    "area_before", "area_after", "width_before", "width_after",
    "height_before", "height_after", "overlap_count_before",
    "overlap_count_after", "spacing_violations", "iterations", "ca_epochs",
}
_BOOL_FIELDS = {"ca_converged", "backend_ok"}


def _coerce(key, val):
    if key in _FLOAT_FIELDS:
        try:
            return float(val)
        except Exception:
            return 0.0
    if key in _INT_FIELDS:
        try:
            return int(val)
        except Exception:
            return 0
    if key in _BOOL_FIELDS:
        return str(val).lower() in ("true", "1", "yes")
    return val


def _run_ca_full(ca_cfg: dict, grid: np.ndarray, policy: str):
    """
    Run a CA visualisation pass with convergence_threshold=0.0 so all
    max_epochs epochs are always executed and the pressure curves are
    guaranteed to have multiple data points.
    """
    sched = build_scheduler(
        ca_cfg, policy,
        max_epochs=20,
        convergence_threshold=0.0,
    )
    return sched.run(grid)


def export_all_figures(config: dict, out_dir: str) -> None:
    figures_dir = os.path.join(out_dir, "figures")
    tables_dir  = os.path.join(out_dir, "tables")
    layouts_dir = os.path.join(out_dir, "compacted_layouts")
    os.makedirs(figures_dir, exist_ok=True)

    dpi = config.get("viz", {}).get("dpi", 150)

    # ── 1. Load ablation metrics from CSV (if available) ─────────────────────
    all_metrics = []
    for csv_path in glob.glob(os.path.join(tables_dir, "*.csv")):
        all_metrics.extend(_load_metrics_from_csv(csv_path))

    if all_metrics:
        area_reduction_bar(
            all_metrics,
            out_path=os.path.join(figures_dir, "area_reduction.png"),
            dpi=dpi,
        )
        width_height_reduction_chart(
            all_metrics,
            out_path=os.path.join(figures_dir, "width_height_reduction.png"),
            dpi=dpi,
        )
        ablation_comparison_chart(
            all_metrics,
            out_path=os.path.join(figures_dir, "ablation_comparison.png"),
            dpi=dpi,
        )

    # ── 2. Load CA config ─────────────────────────────────────────────────────
    ca_config_path = config.get("ca", {}).get("rules_config", "configs/ca_rules.yaml")
    if os.path.isfile(ca_config_path):
        ca_cfg = load_ca_config(ca_config_path)
    else:
        ca_cfg = {}

    reader      = CIFReader()
    discretizer = GridDiscretizer(
        resolution=config.get("ca", {}).get("grid_resolution", 10)
    )

    # ── 3. Per-benchmark figures ──────────────────────────────────────────────
    for demo_cif in glob.glob("data/demo/*.cif"):
        name = os.path.splitext(os.path.basename(demo_cif))[0]
        compacted_cif = os.path.join(layouts_dir, f"{name}_baseline.cif")

        # Occupancy heatmap
        try:
            layout = reader.read(demo_cif)
            grid, _ = discretizer.discretize(layout)
            plot_occupancy_heatmap(
                grid, name,
                out_path=os.path.join(figures_dir, f"{name}_occupancy.png"),
                dpi=dpi,
            )
        except Exception as exc:
            logger.warning("Occupancy heatmap failed for %s: %s", name, exc)

        if not ca_cfg:
            continue

        # Re-read layout fresh for CA runs
        try:
            layout = reader.read(demo_cif)
            grid, _ = discretizer.discretize(layout)
        except Exception as exc:
            logger.warning("Could not read/discretize %s: %s", demo_cif, exc)
            continue

        # ── 3a. Full-epoch convergence curve for full_composite ──────────────
        try:
            ca_result = _run_ca_full(ca_cfg, grid, "full_composite")

            # Pressure heatmap from final epoch
            if ca_result.epoch_results:
                last_ep = ca_result.epoch_results[-1]
                plot_pressure_heatmap(
                    last_ep.state, name, last_ep.epoch,
                    out_path=os.path.join(figures_dir, f"{name}_pressure.png"),
                    dpi=dpi,
                )

            # Four-panel convergence figure — guaranteed multi-point curve
            convergence_curve_full(
                ca_result.epoch_results,
                benchmark_name=name,
                policy="full_composite",
                out_path=os.path.join(
                    figures_dir, f"{name}_convergence.png"
                ),
                dpi=dpi,
            )
        except Exception as exc:
            logger.warning("Convergence figure failed for %s: %s", name, exc)

        # ── 3b. Run all viz policies; collect planning results ────────────────
        planning_results: List[dict] = []
        policy_epoch_data: Dict[str, Tuple[List[float], List[float]]] = {}

        for policy in _VIZ_POLICIES:
            try:
                res = _run_ca_full(ca_cfg, grid, policy)
            except Exception as exc:
                logger.warning("CA run failed for %s/%s: %s", name, policy, exc)
                continue

            xp_hist, yp_hist = res.pressure_history()
            policy_epoch_data[policy] = (xp_hist, yp_hist)

            final_active = (
                res.epoch_results[-1].active_fraction
                if res.epoch_results else 1.0
            )
            planning_results.append({
                "benchmark":             name,
                "policy":                policy,
                "xshrf":                 res.final_xshrf,
                "yshrf":                 res.final_yshrf,
                "ca_epochs":             res.epochs_run,
                "final_active_fraction": final_active,
            })

        # ── 3c. CA planning bar charts (always non-zero, no backend needed) ──
        if planning_results:
            ca_shrink_savings_bar(
                planning_results,
                out_path=os.path.join(
                    figures_dir, f"{name}_ca_shrink_savings.png"
                ),
                dpi=dpi,
            )
            ca_epoch_profile_bar(
                planning_results,
                out_path=os.path.join(
                    figures_dir, f"{name}_ca_epoch_profile.png"
                ),
                dpi=dpi,
            )

        # ── 3d. Multi-policy pressure comparison lines ────────────────────────
        if policy_epoch_data:
            policy_comparison_lines(
                policy_epoch_data,
                benchmark_name=name,
                out_path=os.path.join(
                    figures_dir, f"{name}_policy_comparison.png"
                ),
                dpi=dpi,
            )

        # ── 3e. Before/after snapshot if compacted CIF exists ─────────────────
        if os.path.isfile(compacted_cif):
            try:
                before = reader.read(demo_cif)
                after  = reader.read(compacted_cif)
                plot_before_after(
                    before, after, name,
                    out_path=os.path.join(
                        figures_dir, f"{name}_before_after.png"
                    ),
                    dpi=dpi,
                )
            except Exception as exc:
                logger.warning("Before/after snapshot failed for %s: %s", name, exc)

        # ── 3f. Standard layout rendering ────────────────────────────────────
        try:
            lay = reader.read(demo_cif)
            fig, ax = plt.subplots(figsize=(6, 5))
            fig.patch.set_facecolor("white")
            plot_layout(lay, title=f"Layout: {name}", ax=ax, tech="scmos")
            fig.savefig(
                os.path.join(figures_dir, f"{name}_layout.png"),
                dpi=dpi, bbox_inches="tight", facecolor="white",
            )
            plt.close(fig)
            logger.info("Standard layout figure: %s", name)
        except Exception as exc:
            logger.warning("Standard layout failed for %s: %s", name, exc)

        # ── 3g. Magic-style layout rendering ─────────────────────────────────
        try:
            lay = reader.read(demo_cif)
            plot_magic_layout(
                lay,
                title=f"Magic Layout: {name}",
                tech="scmos",
                out_path=os.path.join(figures_dir, f"{name}_magic_layout.png"),
                dpi=dpi,
            )
            logger.info("Magic layout figure: %s", name)
        except Exception as exc:
            logger.warning("Magic layout failed for %s: %s", name, exc)

        # ── 3h. Congestion heatmap ────────────────────────────────────────────
        try:
            plot_congestion_heatmap(
                grid, name,
                out_path=os.path.join(figures_dir, f"{name}_congestion.png"),
                dpi=dpi,
            )
        except Exception as exc:
            logger.warning("Congestion heatmap failed for %s: %s", name, exc)

        # ── 3i. Rule-110 visualizations ───────────────────────────────────────
        try:
            r110_sched = Rule110Scheduler(max_epochs=20, mode="alternating",
                                          damping=0.85)
            r110_result = r110_sched.run(grid)

            plot_state_evolution(
                r110_result, name,
                out_path=os.path.join(figures_dir, f"{name}_r110_evolution.png"),
                dpi=dpi,
            )
            plot_pressure_evolution(
                r110_result, name,
                out_path=os.path.join(figures_dir, f"{name}_r110_pressure_evolution.png"),
                dpi=dpi,
            )
            plot_shrink_trajectory(
                r110_result, name,
                out_path=os.path.join(figures_dir, f"{name}_r110_shrink.png"),
                dpi=dpi,
            )
            plot_activity_curve(
                r110_result, name,
                out_path=os.path.join(figures_dir, f"{name}_r110_activity.png"),
                dpi=dpi,
            )
            plot_pressure_profiles(
                r110_result, name,
                out_path=os.path.join(figures_dir, f"{name}_r110_pressure_profiles.png"),
                dpi=dpi,
            )
            plot_r110_dashboard(
                r110_result, grid, name,
                out_path=os.path.join(figures_dir, f"{name}_r110_dashboard.png"),
                dpi=dpi,
            )
            plot_policy_matrix(
                grid, name,
                out_path=os.path.join(figures_dir, f"{name}_r110_policy_matrix.png"),
                dpi=dpi,
            )
            plot_shrink_comparison(
                grid, name,
                out_path=os.path.join(figures_dir, f"{name}_r110_shrink_comparison.png"),
                dpi=dpi,
            )
            logger.info("Rule-110 figures complete: %s", name)
        except Exception as exc:
            logger.warning("Rule-110 figures failed for %s: %s", name, exc)

    logger.info("Figure export complete. Output: %s", figures_dir)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config",  default="configs/default.yaml")
    parser.add_argument("--out-dir", default="outputs")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    with open(args.config) as fh:
        config = yaml.safe_load(fh)

    export_all_figures(config, args.out_dir)


if __name__ == "__main__":
    main()
