"""
Ablation study runner.
Iterates over all defined CA policies and collects comparative metrics.
"""

import os
import logging
import argparse
import yaml
import pandas as pd
from typing import List

from ..ca.composite_rules import load_ca_config, all_policy_names
from .baseline_eval import run_baseline
from .ca_eval import run_ca_eval
from .metrics_reporter import CompactionMetrics, write_csv, write_markdown_table

logger = logging.getLogger(__name__)


def run_ablation(
    config: dict,
    ca_config_path: str,
    benchmarks_cfg: str,
    out_dir: str,
) -> List[CompactionMetrics]:
    ca_cfg   = load_ca_config(ca_config_path)
    policies = all_policy_names(ca_cfg)

    all_metrics: List[CompactionMetrics] = []

    # Baseline (no CA)
    logger.info("=== Ablation: baseline ===")
    baseline = run_baseline(config, benchmarks_cfg, out_dir)
    all_metrics.extend(baseline)

    # Each CA policy
    for policy in policies:
        logger.info("=== Ablation: %s ===", policy)
        metrics = run_ca_eval(
            config, ca_config_path, benchmarks_cfg, policy, out_dir
        )
        all_metrics.extend(metrics)

    # Combined output
    tables_dir = os.path.join(out_dir, "tables")
    write_csv(all_metrics,            os.path.join(tables_dir, "ablation_results.csv"))
    write_markdown_table(all_metrics, os.path.join(tables_dir, "ablation_results.md"))

    # Pivot summary: one row per benchmark, columns = policies
    _write_pivot(all_metrics, tables_dir)

    return all_metrics


def _write_pivot(all_metrics: List[CompactionMetrics], tables_dir: str) -> None:
    """Write a wide-format comparison table (benchmarks x policies)."""
    from dataclasses import asdict
    rows = [asdict(m) for m in all_metrics if not m.notes.startswith("SKIP")]
    if not rows:
        return
    try:
        df = pd.DataFrame(rows)
        pivot = df.pivot_table(
            index="benchmark",
            columns="policy",
            values=["area_reduction_pct", "width_reduction_pct", "height_reduction_pct",
                    "runtime_seconds"],
            aggfunc="first",
        )
        pivot.to_csv(os.path.join(tables_dir, "ablation_pivot.csv"))
        logger.info("Pivot table written to %s/ablation_pivot.csv", tables_dir)
    except Exception as exc:
        logger.warning("Could not write pivot table: %s", exc)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config",     default="configs/default.yaml")
    parser.add_argument("--ca-config",  default="configs/ca_rules.yaml")
    parser.add_argument("--benchmarks", default="configs/benchmarks.yaml")
    parser.add_argument("--out-dir",    default="outputs")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    with open(args.config) as fh:
        config = yaml.safe_load(fh)

    run_ablation(config, args.ca_config, args.benchmarks, args.out_dir)


if __name__ == "__main__":
    main()
