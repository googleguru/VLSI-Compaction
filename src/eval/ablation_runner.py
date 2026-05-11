"""
Ablation study runner.

Supports two CA back-ends:
  - Rule-110 (primary):  alternating row/column Rule-110 passes
  - 7-rule composite:    legacy multi-rule scheduler (kept for comparison)

Policies run:
  Rule-110 ablations (from configs/rule110.yaml['ablations'])
    r110_row_only, r110_col_only, r110_alternating, r110_alternating_adaptive
  Legacy composite ablations (from configs/ca_rules.yaml['ablations'])
    kept for framework continuity; clearly labelled in output tables

All results share the CompactionMetrics schema and are written to the same
CSV/Markdown tables so a single pivot table covers both CA strategies.
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
from .rule110_eval import run_rule110_eval
from .metrics_reporter import CompactionMetrics, write_csv, write_markdown_table

logger = logging.getLogger(__name__)


def run_ablation(
    config: dict,
    ca_config_path: str,
    rule110_config_path: str,
    benchmarks_cfg: str,
    out_dir: str,
) -> List[CompactionMetrics]:

    ca_cfg          = load_ca_config(ca_config_path)
    legacy_policies = all_policy_names(ca_cfg)

    with open(rule110_config_path) as fh:
        r110_cfg = yaml.safe_load(fh)
    r110_policies = _rule110_policy_names(r110_cfg)

    all_metrics: List[CompactionMetrics] = []

    # 1. Backend-only baseline
    logger.info("=== Ablation: baseline (no CA) ===")
    all_metrics.extend(run_baseline(config, benchmarks_cfg, out_dir))

    # 2. Rule-110 ablations (primary CA)
    for policy in r110_policies:
        logger.info("=== Ablation Rule-110: %s ===", policy)
        all_metrics.extend(
            run_rule110_eval(config, r110_cfg, benchmarks_cfg, policy, out_dir)
        )

    # 3. Legacy composite ablations (comparison)
    for policy in legacy_policies:
        logger.info("=== Ablation composite: %s ===", policy)
        all_metrics.extend(
            run_ca_eval(config, ca_config_path, benchmarks_cfg, policy, out_dir)
        )

    logger.info(
        "=== Rule-110 topology comparison ===\n"
        "    see r110_row_only / r110_col_only / r110_alternating rows"
    )

    tables_dir = os.path.join(out_dir, "tables")
    write_csv(all_metrics,            os.path.join(tables_dir, "ablation_results.csv"))
    write_markdown_table(all_metrics, os.path.join(tables_dir, "ablation_results.md"))
    _write_pivot(all_metrics, tables_dir)
    _write_r110_comparison(all_metrics, tables_dir)

    return all_metrics


def _rule110_policy_names(r110_cfg: dict) -> List[str]:
    return [k for k in r110_cfg.get("ablations", {}) if k != "backend_only"]


def _write_pivot(all_metrics: List[CompactionMetrics], tables_dir: str) -> None:
    from dataclasses import asdict
    rows = [asdict(m) for m in all_metrics if not m.notes.startswith("ERROR")]
    if not rows:
        return
    try:
        df    = pd.DataFrame(rows)
        pivot = df.pivot_table(
            index   = "benchmark",
            columns = "policy",
            values  = [
                "area_reduction_pct", "width_reduction_pct",
                "height_reduction_pct", "runtime_seconds",
                "spacing_violations", "ca_epochs",
            ],
            aggfunc = "first",
        )
        pivot.to_csv(os.path.join(tables_dir, "ablation_pivot.csv"))
        logger.info("Pivot table written to %s/ablation_pivot.csv", tables_dir)
    except Exception as exc:
        logger.warning("Could not write pivot table: %s", exc)


def _write_r110_comparison(
    all_metrics: List[CompactionMetrics], tables_dir: str
) -> None:
    r110_policies = {
        "r110_row_only", "r110_col_only",
        "r110_alternating", "r110_alternating_adaptive",
    }
    rows = [m for m in all_metrics if m.policy in r110_policies]
    if not rows:
        return
    try:
        from dataclasses import asdict
        df = pd.DataFrame([asdict(m) for m in rows])
        df.to_csv(
            os.path.join(tables_dir, "rule110_comparison.csv"), index=False
        )
        logger.info("Rule-110 comparison table written.")
    except Exception as exc:
        logger.warning("Rule-110 comparison table failed: %s", exc)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config",         default="configs/default.yaml")
    parser.add_argument("--ca-config",      default="configs/ca_rules.yaml")
    parser.add_argument("--rule110-config", default="configs/rule110.yaml")
    parser.add_argument("--benchmarks",     default="configs/benchmarks.yaml")
    parser.add_argument("--out-dir",        default="outputs")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    with open(args.config) as fh:
        config = yaml.safe_load(fh)

    run_ablation(
        config, args.ca_config, args.rule110_config,
        args.benchmarks, args.out_dir,
    )


if __name__ == "__main__":
    main()
