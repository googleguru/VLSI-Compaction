"""
CA-enhanced compaction evaluation.
Runs the CA planning layer before each backend compaction call.
"""

import os
import logging
import argparse
import yaml
import numpy as np

from ..io.benchmark_manifest import BenchmarkManifest
from ..io.cif_reader import CIFReader
from ..ca.grid_discretizer import GridDiscretizer
from ..ca.composite_rules import load_ca_config, build_scheduler
from ..planning.shrink_factor_planner import plan_shrink_factors
from ..planning.iteration_scheduler import plan_iterations
from ..backend.perl_wrapper import PerlCompactionWrapper, CompactionRequest
from ..geometry.spatial_metrics import summarize_reduction
from ..geometry.overlap_estimator import count_bbox_overlaps
from .metrics_reporter import CompactionMetrics, write_csv, write_markdown_table

logger = logging.getLogger(__name__)


def run_ca_eval(
    config: dict,
    ca_config_path: str,
    benchmarks_cfg: str,
    policy: str,
    out_dir: str,
) -> list:
    manifest    = BenchmarkManifest(benchmarks_cfg)
    ca_cfg      = load_ca_config(ca_config_path)
    backend_cfg = config.get("backend", {})
    perl_script = backend_cfg.get("perl_script", "vendor/cellCompaction.pl")
    timeout     = backend_cfg.get("timeout_seconds", 300)
    base_iters  = backend_cfg.get("default_iter", 5)
    ca_cfg_exp  = config.get("ca", {})

    wrapper    = PerlCompactionWrapper(script_path=perl_script)
    reader     = CIFReader()
    discretizer = GridDiscretizer(resolution=ca_cfg_exp.get("grid_resolution", 10))
    all_metrics: list = []

    for entry in manifest.skipped():
        reason = (entry.skip_reason or "file not found").strip().replace("\n", " ")[:120]
        all_metrics.append(CompactionMetrics.skipped(entry.name, policy, reason))

    for entry in manifest.ready():
        logger.info("[CA-RUN] %s  policy=%s", entry.name, policy)

        layout_before = reader.read(entry.path)
        bbox_before   = layout_before.geometry_bbox()
        bboxes_before = layout_before._collect_all_geometry()

        # --- CA planning phase ---
        grid, _  = discretizer.discretize(layout_before)
        occupancy_ratio = float(np.mean(grid == GridDiscretizer.OCCUPIED))

        scheduler = build_scheduler(
            ca_cfg,
            policy_name  = policy,
            max_epochs   = ca_cfg_exp.get("max_epochs", 20),
            neighborhood = ca_cfg_exp.get("neighborhood", "moore"),
            convergence_threshold = ca_cfg_exp.get("convergence_threshold", 0.01),
        )
        ca_result = scheduler.run(grid)
        xshrf, yshrf = plan_shrink_factors(
            ca_result, occupancy_ratio,
            base_xshrf = backend_cfg.get("default_xshrf", 0.9),
            base_yshrf = backend_cfg.get("default_yshrf", 0.9),
        )
        n_iters = plan_iterations(ca_result, base_iters)

        logger.debug(
            "CA done: epochs=%d converged=%s xshrf=%.4f yshrf=%.4f iters=%d",
            ca_result.epochs_run, ca_result.converged, xshrf, yshrf, n_iters,
        )

        # --- Backend compaction phase ---
        out_cif = os.path.join(
            out_dir, "compacted_layouts", f"{entry.name}_{policy}.cif"
        )
        os.makedirs(os.path.dirname(out_cif), exist_ok=True)

        req = CompactionRequest(
            input_cif  = entry.path,
            output_cif = out_cif,
            iterations = n_iters,
            xshrf      = xshrf,
            yshrf      = yshrf,
            timeout    = timeout,
        )
        result = wrapper.run(req)

        if result.ok and result.layout is not None:
            bbox_after   = result.layout.geometry_bbox()
            bboxes_after = result.layout._collect_all_geometry()
            reduction    = summarize_reduction(bbox_before, bbox_after)

            m = CompactionMetrics(
                benchmark             = entry.name,
                policy                = policy,
                area_before           = reduction["area_before"],
                area_after            = reduction["area_after"],
                area_reduction_pct    = reduction["area_reduction_pct"],
                width_before          = reduction["width_before"],
                width_after           = reduction["width_after"],
                width_reduction_pct   = reduction["width_reduction_pct"],
                height_before         = reduction["height_before"],
                height_after          = reduction["height_after"],
                height_reduction_pct  = reduction["height_reduction_pct"],
                overlap_count_before  = count_bbox_overlaps(bboxes_before),
                overlap_count_after   = count_bbox_overlaps(bboxes_after),
                runtime_seconds       = result.metadata.runtime_seconds,
                iterations            = n_iters,
                xshrf                 = xshrf,
                yshrf                 = yshrf,
                ca_epochs             = ca_result.epochs_run,
                ca_converged          = ca_result.converged,
                backend_ok            = True,
            )
        else:
            warnings = "; ".join(result.metadata.backend_warnings[:3])
            m = CompactionMetrics(
                benchmark    = entry.name,
                policy       = policy,
                ca_epochs    = ca_result.epochs_run,
                ca_converged = ca_result.converged,
                backend_ok   = False,
                notes        = f"backend failed: {warnings}",
            )

        all_metrics.append(m)

    tables_dir = os.path.join(out_dir, "tables")
    write_csv(all_metrics, os.path.join(tables_dir, f"ca_results_{policy}.csv"))
    write_markdown_table(all_metrics, os.path.join(tables_dir, f"ca_results_{policy}.md"))
    return all_metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config",     default="configs/default.yaml")
    parser.add_argument("--ca-config",  default="configs/ca_rules.yaml")
    parser.add_argument("--benchmarks", default="configs/benchmarks.yaml")
    parser.add_argument("--policy",     default="full_composite")
    parser.add_argument("--out-dir",    default="outputs")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    with open(args.config) as fh:
        config = yaml.safe_load(fh)

    run_ca_eval(config, args.ca_config, args.benchmarks, args.policy, args.out_dir)


if __name__ == "__main__":
    main()
