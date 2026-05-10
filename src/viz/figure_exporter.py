"""
Publication-ready figure exporter.
Reads evaluation results and CA run data to produce all required figures.
"""

import os
import csv
import glob
import logging
import argparse
import yaml
import numpy as np
from dataclasses import dataclass
from typing import List, Optional

from ..io.cif_reader import CIFReader
from ..ca.grid_discretizer import GridDiscretizer
from ..ca.composite_rules import load_ca_config, build_scheduler
from .layout_plotter import plot_before_after
from .chart_generator import (
    area_reduction_bar,
    width_height_reduction_chart,
    convergence_curve,
    ablation_comparison_chart,
)
from .heatmap_plotter import (
    plot_occupancy_heatmap,
    plot_pressure_heatmap,
    plot_congestion_heatmap,
)

logger = logging.getLogger(__name__)


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
        try: return float(val)
        except: return 0.0
    if key in _INT_FIELDS:
        try: return int(val)
        except: return 0
    if key in _BOOL_FIELDS:
        return str(val).lower() in ("true", "1", "yes")
    return val


def export_all_figures(config: dict, out_dir: str) -> None:
    figures_dir = os.path.join(out_dir, "figures")
    tables_dir  = os.path.join(out_dir, "tables")
    layouts_dir = os.path.join(out_dir, "compacted_layouts")
    os.makedirs(figures_dir, exist_ok=True)

    dpi = config.get("viz", {}).get("dpi", 150)

    # 1. Load all metrics
    all_metrics = []
    for csv_path in glob.glob(os.path.join(tables_dir, "*.csv")):
        all_metrics.extend(_load_metrics_from_csv(csv_path))

    if all_metrics:
        # 2. Area reduction bar
        area_reduction_bar(
            all_metrics,
            out_path=os.path.join(figures_dir, "area_reduction.png"),
            dpi=dpi,
        )
        # 3. Width/height reduction
        width_height_reduction_chart(
            all_metrics,
            out_path=os.path.join(figures_dir, "width_height_reduction.png"),
            dpi=dpi,
        )
        # 4. Ablation comparison
        ablation_comparison_chart(
            all_metrics,
            out_path=os.path.join(figures_dir, "ablation_comparison.png"),
            dpi=dpi,
        )

    # 5. Per-benchmark before/after snapshots + occupancy/pressure heatmaps
    reader       = CIFReader()
    discretizer  = GridDiscretizer(resolution=config.get("ca", {}).get("grid_resolution", 10))

    ca_config_path = config.get("ca", {}).get("rules_config", "configs/ca_rules.yaml")
    if os.path.isfile(ca_config_path):
        ca_cfg = load_ca_config(ca_config_path)
    else:
        ca_cfg = {}

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

        # Pressure heatmap + convergence (CA dry-run on demo)
        try:
            layout = reader.read(demo_cif)
            grid, _ = discretizer.discretize(layout)
            if ca_cfg:
                sched = build_scheduler(ca_cfg, "full_composite", max_epochs=10)
                ca_result = sched.run(grid)
                if ca_result.epoch_results:
                    last_ep = ca_result.epoch_results[-1]
                    plot_pressure_heatmap(
                        last_ep.state, name, last_ep.epoch,
                        out_path=os.path.join(figures_dir, f"{name}_pressure.png"),
                        dpi=dpi,
                    )
                xhist, yhist = ca_result.pressure_history()
                convergence_curve(
                    xhist, yhist, name, "full_composite",
                    out_path=os.path.join(figures_dir, f"{name}_convergence.png"),
                    dpi=dpi,
                )
        except Exception as exc:
            logger.warning("Pressure/convergence figure failed for %s: %s", name, exc)

        # Before/after snapshot if compacted CIF exists
        if os.path.isfile(compacted_cif):
            try:
                before = reader.read(demo_cif)
                after  = reader.read(compacted_cif)
                plot_before_after(
                    before, after, name,
                    out_path=os.path.join(figures_dir, f"{name}_before_after.png"),
                    dpi=dpi,
                )
            except Exception as exc:
                logger.warning("Before/after snapshot failed for %s: %s", name, exc)

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
