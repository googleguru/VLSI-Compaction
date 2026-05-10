"""
Iteration scheduler: decides how many backend compaction iterations to run
and how to split them across X and Y phases.
"""

import logging
from typing import List, Tuple
from ..ca.epoch_scheduler import CARunResult
from .directional_pressure import extract_dominant_direction, derive_iteration_schedule

logger = logging.getLogger(__name__)


def plan_iterations(
    ca_result: CARunResult,
    base_iters: int = 5,
    max_iters: int = 10,
) -> int:
    """
    Decide the total number of backend iterations.
    Fewer CA epochs needed -> fewer backend iterations required.
    """
    epochs_run = ca_result.epochs_run
    if ca_result.converged:
        # Fast convergence suggests a simpler layout -> fewer iterations
        iters = max(2, min(base_iters, epochs_run))
    else:
        iters = min(max_iters, base_iters + 2)

    logger.debug(
        "IterationScheduler: ca_epochs=%d converged=%s -> backend_iters=%d",
        epochs_run, ca_result.converged, iters,
    )
    return iters


def full_compaction_plan(
    ca_result: CARunResult,
    base_iters: int = 5,
) -> List[Tuple[int, float, float]]:
    """
    Return a list of (iteration_number, xshrf, yshrf) tuples for the backend.
    """
    n_iters = plan_iterations(ca_result, base_iters)
    schedule = derive_iteration_schedule(ca_result, n_iters)
    return [(i + 1, xs, ys) for i, (xs, ys) in enumerate(schedule)]
