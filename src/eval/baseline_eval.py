"""
Baseline evaluation: backend-only compaction with no CA planning.
Runs cellCompaction.pl with default parameters on all available benchmarks.
"""

import os
import logging
import argparse
import yaml
from pathlib import Path

from ..io.benchmark_manifest import BenchmarkManifest
from ..io.cif_reader import CIFReader
from ..backend.perl_wrapper import PerlCompactionWrapper, CompactionRequest
from ..geometry.spatial_metrics import summarize_reduction
from ..geometry.overlap_estimator import count_bbox_overlaps
from .metrics_reporter import CompactionMetrics, write_csv, write_markdown_table

logger = logging.getLogger(__name__)


def run_baseline(
    config: dict,
    benchmarks_cfg: str,
    out_dir: str,
) -> list:
    manifest = BenchmarkManifest(benchmarks_cfg)
    manifest.log_summary()

    backend_cfg = config.get("backend", {})
    perl_script  = backend_cfg.get("perl_script", "vendor/cellCompaction.pl")
    default_iter = backend_cfg.get("default_iter", 5)
    default_xs   = backend_cfg.get("default_xshrf", 0.9)
    default_ys   = backend_cfg.get("default_yshrf", 0.9)
    timeout      = backend_cfg.get("timeout_seconds", 300)

    wrapper  = PerlCompactionWrapper(script_path=perl_script)
    reader   = CIFReader()
    all_metrics: list = []

    ready    = manifest.ready()
    skipped  = manifest.skipped()

    for entry in skipped:
        reason = (entry.skip_reason or "file not found").strip().replace("\n", " ")[:120]
        m = CompactionMetrics.skipped(entry.name, "baseline", reason)
        all_metrics.append(m)
        logger.info("[SKIP] %s: %s", entry.name, reason[:80])

    for entry in ready:
        logger.info("[RUN ] %s", entry.name)
        out_cif = os.path.join(out_dir, "compacted_layouts", f"{entry.name}_baseline.cif")
        os.makedirs(os.path.dirname(out_cif), exist_ok=True)

        layout_before = reader.read(entry.path)
        bbox_before   = layout_before.geometry_bbox()
        bboxes_before = layout_before._collect_all_geometry()

        req = CompactionRequest(
            input_cif  = entry.path,
            output_cif = out_cif,
            iterations = default_iter,
            xshrf      = default_xs,
            yshrf      = default_ys,
            timeout    = timeout,
        )
        result = wrapper.run(req)

        if result.ok and result.layout is not None:
            bbox_after   = result.layout.geometry_bbox()
            bboxes_after = result.layout._collect_all_geometry()
            reduction    = summarize_reduction(bbox_before, bbox_after)

            m = CompactionMetrics(
                benchmark             = entry.name,
                policy                = "baseline",
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
                iterations            = default_iter,
                xshrf                 = default_xs,
                yshrf                 = default_ys,
                backend_ok            = True,
            )
        else:
            warnings = "; ".join(result.metadata.backend_warnings[:3])
            m = CompactionMetrics(
                benchmark  = entry.name,
                policy     = "baseline",
                backend_ok = False,
                notes      = f"backend failed: {warnings}",
            )

        all_metrics.append(m)

    tables_dir = os.path.join(out_dir, "tables")
    write_csv(all_metrics,              os.path.join(tables_dir, "baseline_results.csv"))
    write_markdown_table(all_metrics,   os.path.join(tables_dir, "baseline_results.md"))
    return all_metrics


def main():
    parser = argparse.ArgumentParser(description="Baseline backend-only evaluation")
    parser.add_argument("--config",      default="configs/default.yaml")
    parser.add_argument("--benchmarks",  default="configs/benchmarks.yaml")
    parser.add_argument("--out-dir",     default="outputs")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    with open(args.config) as fh:
        config = yaml.safe_load(fh)

    run_baseline(config, args.benchmarks, args.out_dir)


if __name__ == "__main__":
    main()
