"""
Ablation study runner.

Iterates over all CA policies defined in ca_rules.yaml['ablations'] and
the default full_composite, plus an explicit Moore vs Von Neumann topology
comparison for the full composite policy.

Policies that declare `neighborhood: vonneumann` in their YAML spec
automatically run with the 4-connected kernel via build_scheduler.
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

    # 1. Backend-only baseline (no CA layer)
    logger.info("=== Ablation: baseline ===")
    baseline = run_baseline(config, benchmarks_cfg, out_dir)
    all_metrics.extend(baseline)

    # 2. Each CA policy (rule ablations + topology variants)
    for policy in policies:
        logger.info("=== Ablation: %s ===", policy)
        metrics = run_ca_eval(
            config, ca_config_path, benchmarks_cfg, policy, out_dir
        )
        all_metrics.extend(metrics)

    # 3. Explicit neighborhood comparison:
    #    full_composite with Moore (already covered above as "full_composite")
    #    full_composite with vonneumann (covered by "vonneumann_composite" policy).
    #    Log a clear section header so results are easy to locate in the log.
    logger.info(
        "=== Neighborhood comparison: full_composite(moore) vs vonneumann_composite ===\n"
        "    moore results: see policy='full_composite' rows\n"
        "    vonneumann results: see policy='vonneumann_composite' rows"
    )

    # Combined output
    tables_dir = os.path.join(out_dir, "tables")
    write_csv(all_metrics,            os.path.join(tables_dir, "ablation_results.csv"))
    write_markdown_table(all_metrics, os.path.join(tables_dir, "ablation_results.md"))

    _write_pivot(all_metrics, tables_dir)
    _write_neighborhood_comparison(all_metrics, tables_dir)

    return all_metrics


def _write_pivot(all_metrics: List[CompactionMetrics], tables_dir: str) -> None:
    """Wide-format comparison table: benchmarks × policies."""
    from dataclasses import asdict
    rows = [asdict(m) for m in all_metrics if not m.notes.startswith("SKIP")]
    if not rows:
        return
    try:
        df = pd.DataFrame(rows)
        pivot = df.pivot_table(
            index="benchmark",
            columns="policy",
            values=[
                "area_reduction_pct", "width_reduction_pct",
                "height_reduction_pct", "runtime_seconds",
                "spacing_violations",
            ],
            aggfunc="first",
        )
        pivot.to_csv(os.path.join(tables_dir, "ablation_pivot.csv"))
        logger.info("Pivot table written to %s/ablation_pivot.csv", tables_dir)
    except Exception as exc:
        logger.warning("Could not write pivot table: %s", exc)


def _write_neighborhood_comparison(
    all_metrics: List[CompactionMetrics], tables_dir: str
) -> None:
    """
    Isolated Moore vs Von Neumann comparison table.
    Compares full_composite (Moore) against vonneumann_composite.
    """
    from dataclasses import asdict
    nb_policies = {"full_composite", "vonneumann_composite"}
    rows = [
        asdict(m) for m in all_metrics
        if m.policy in nb_policies and not m.notes.startswith("SKIP")
    ]
    if not rows:
        return
    try:
        df = pd.DataFrame(rows)
        df["topology"] = df["policy"].map({
            "full_composite":      "Moore (8-connected)",
            "vonneumann_composite": "Von Neumann (4-connected)",
        })
        out = df[[
            "benchmark", "topology",
            "area_reduction_pct", "width_reduction_pct", "height_reduction_pct",
            "spacing_violations", "ca_epochs", "ca_converged", "runtime_seconds",
        ]].sort_values(["benchmark", "topology"])
        out.to_csv(
            os.path.join(tables_dir, "neighborhood_comparison.csv"), index=False
        )
        logger.info("Neighborhood comparison written to %s/neighborhood_comparison.csv",
                    tables_dir)
    except Exception as exc:
        logger.warning("Could not write neighborhood comparison: %s", exc)


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
