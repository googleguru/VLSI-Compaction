"""
Rule-110 CA evaluation runner.

Runs one ablation policy over all available benchmarks:
1. Reads the benchmark CIF (or generates synthetic layout).
2. Discretizes to an occupancy grid.
3. Runs the Rule-110 scheduler with the given policy.
4. Extracts shrink factors via the planning layer.
5. Calls the Perl compaction backend.
6. Exports .mag files (before/after) via MagWriter.
7. Optionally runs Magic DRC on the compacted layout.
8. Measures and returns CompactionMetrics.
"""

import os
import time
import logging
from typing import List

from ..io.cif_reader import CIFReader
from ..io.cif_writer import write_cif
from ..io.mag_writer import write_mag_flat
from ..io.benchmark_manifest import BenchmarkManifest
from ..io.geometry_normalizer import normalize_layout
from ..ca.grid_discretizer import GridDiscretizer
from ..ca.rule110_scheduler import Rule110Scheduler
from ..planning.shrink_factor_planner import plan_shrink_factors
from ..backend.perl_wrapper import PerlCompactor
from ..geometry.overlap_estimator import count_bbox_overlaps, spacing_violations
from ..geometry.spatial_metrics import bounding_box_area, layout_bboxes
from ..layout.magic_runner import MagicRunner
from .metrics_reporter import CompactionMetrics
from .magic_drc_helper import drc_violations

logger = logging.getLogger(__name__)


def run_rule110_eval(
    config: dict,
    rule110_config: dict,
    benchmarks_cfg: str,
    policy_name: str,
    out_dir: str,
) -> List[CompactionMetrics]:
    """
    Run Rule-110 guided compaction for *policy_name* on all enabled benchmarks.
    """
    manifest    = BenchmarkManifest(benchmarks_cfg)
    reader      = CIFReader()
    discretizer = GridDiscretizer(
        resolution=config.get("ca", {}).get("grid_resolution", 10)
    )
    compactor = PerlCompactor(
        script_path = config.get("backend", {}).get("perl_script", "vendor/cellCompaction.pl"),
        timeout     = config.get("backend", {}).get("timeout_seconds", 300),
    )

    layout_cfg  = config.get("layout", {})
    magic_tech  = layout_cfg.get("magic_tech", "scmos")
    magic_runner = MagicRunner(
        magic_bin = layout_cfg.get("magic_bin", "magic"),
        tech      = magic_tech,
    )

    sched_cfg = _policy_config(rule110_config, policy_name)
    scheduler = Rule110Scheduler(
        max_epochs  = sched_cfg.get("max_epochs",  20),
        boundary    = sched_cfg.get("boundary",    "clamped"),
        damping     = sched_cfg.get("damping",     0.85),
        mode        = sched_cfg.get("mode",        "alternating"),
        min_shrink  = sched_cfg.get("min_shrink",  0.80),
        max_shrink  = sched_cfg.get("max_shrink",  0.99),
        seed        = config.get("experiment", {}).get("seed", 42),
    )

    all_metrics: List[CompactionMetrics] = []

    for bm in manifest.available_benchmarks():
        bm_out = os.path.join(out_dir, "compacted")
        os.makedirs(bm_out, exist_ok=True)

        try:
            metrics = _run_one(
                bm, config, policy_name, scheduler, discretizer,
                reader, compactor, magic_runner, magic_tech, bm_out,
            )
        except Exception as exc:
            logger.error("Rule110 eval failed [%s/%s]: %s", bm.name, policy_name, exc)
            metrics = CompactionMetrics(
                benchmark = bm.name,
                policy    = policy_name,
                notes     = f"ERROR: {exc}",
            )
        all_metrics.append(metrics)

    return all_metrics


def _run_one(
    bm, config, policy_name, scheduler, discretizer,
    reader, compactor, magic_runner, magic_tech, out_dir,
) -> CompactionMetrics:
    t_start = time.perf_counter()

    layout_before = reader.read(bm.path)
    layout_before = normalize_layout(layout_before)

    bboxes_before = layout_bboxes(layout_before)
    area_before   = bounding_box_area(layout_before)
    w_before, h_before = _wh(layout_before)

    # CA planning
    t_ca = time.perf_counter()
    grid, _ = discretizer.discretize(layout_before)
    run_result = scheduler.run(grid)
    ca_time = time.perf_counter() - t_ca

    occ_ratio = float(grid.mean())
    xshrf, yshrf = plan_shrink_factors(run_result, occ_ratio)

    # Write CIF and .mag (before)
    in_cif  = os.path.join(out_dir, f"{bm.name}_in.cif")
    out_cif = os.path.join(out_dir, f"{bm.name}_{policy_name}.cif")
    write_cif(layout_before, in_cif)
    mag_dir = os.path.join(out_dir, "mag")
    try:
        write_mag_flat(layout_before,
                       os.path.join(mag_dir, f"{bm.name}_before.mag"),
                       tech=magic_tech)
    except Exception as exc:
        logger.debug("mag export (before) failed: %s", exc)

    backend_ok = False
    area_after, w_after, h_after = area_before, w_before, h_before
    bboxes_after = bboxes_before
    layout_after = layout_before
    backend_iters = config.get("backend", {}).get("default_iter", 5)

    comp_result = compactor.compact(
        input_cif  = in_cif,
        output_cif = out_cif,
        iterations = backend_iters,
        xshrf      = xshrf,
        yshrf      = yshrf,
    )

    if comp_result.success and os.path.isfile(out_cif):
        try:
            layout_after = reader.read(out_cif)
            area_after   = bounding_box_area(layout_after)
            w_after, h_after = _wh(layout_after)
            bboxes_after = layout_bboxes(layout_after)
            backend_ok   = True
            # Export compacted .mag
            try:
                write_mag_flat(layout_after,
                               os.path.join(mag_dir, f"{bm.name}_{policy_name}_after.mag"),
                               tech=magic_tech)
            except Exception as exc:
                logger.debug("mag export (after) failed: %s", exc)
        except Exception as exc:
            logger.warning("Could not read compacted CIF: %s", exc)

    total_time = time.perf_counter() - t_start

    def _pct(before, after):
        if before <= 0:
            return 0.0
        return round((before - after) / before * 100, 2)

    sp_lam = config.get("geometry", {}).get("spacing_lambda", 1)
    drc_cif = out_cif if backend_ok else in_cif
    n_drc, magic_used = drc_violations(
        drc_cif, bboxes_after, sp_lam, magic_runner, magic_tech
    )

    return CompactionMetrics(
        benchmark               = bm.name,
        policy                  = policy_name,
        area_before             = area_before,
        area_after              = area_after,
        area_reduction_pct      = _pct(area_before, area_after),
        width_before            = w_before,
        width_after             = w_after,
        width_reduction_pct     = _pct(w_before, w_after),
        height_before           = h_before,
        height_after            = h_after,
        height_reduction_pct    = _pct(h_before, h_after),
        overlap_count_before    = count_bbox_overlaps(bboxes_before),
        overlap_count_after     = count_bbox_overlaps(bboxes_after),
        spacing_violations      = spacing_violations(bboxes_after, sp_lam),
        magic_drc_violations    = n_drc if magic_used else -1,
        magic_drc_available     = magic_used,
        ca_epochs               = run_result.epochs_run,
        ca_converged            = False,
        ca_planning_seconds     = round(ca_time, 3),
        runtime_seconds         = round(total_time, 3),
        xshrf                   = xshrf,
        yshrf                   = yshrf,
        backend_ok              = backend_ok,
        iterations              = backend_iters,
        notes                   = "",
    )


def _wh(layout):
    from ..geometry.spatial_metrics import layout_width_height
    return layout_width_height(layout)


def _policy_config(rule110_config: dict, policy_name: str) -> dict:
    ablations = rule110_config.get("ablations", {})
    if policy_name in ablations:
        return ablations[policy_name]
    return rule110_config.get("defaults", {})
