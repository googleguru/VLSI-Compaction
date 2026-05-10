"""
Directional pressure planner: maps CA epoch results to backend compaction hints.
"""

import numpy as np
import logging
from typing import List, Tuple
from ..ca.epoch_scheduler import CARunResult

logger = logging.getLogger(__name__)


def extract_dominant_direction(ca_result: CARunResult) -> str:
    """Return 'x', 'y', or 'both' based on net CA pressure."""
    if not ca_result.epoch_results:
        return "both"
    last = ca_result.epoch_results[-1]
    pres = last.aggregate_pressure
    xp = abs(pres.get("net_xp", 0.0))
    yp = abs(pres.get("net_yp", 0.0))
    if xp > 2 * yp:
        return "x"
    if yp > 2 * xp:
        return "y"
    return "both"


def derive_iteration_schedule(
    ca_result: CARunResult,
    base_iters: int = 5,
) -> List[Tuple[float, float]]:
    """
    Return a list of (xshrf, yshrf) tuples for each planned backend iteration.
    Derived from the CA epoch results' suggested shrink factors.
    """
    epochs = ca_result.epoch_results
    if not epochs:
        return [(0.9, 0.9)] * base_iters

    # Sample evenly across epochs
    n = min(base_iters, len(epochs))
    indices = [int(i * (len(epochs) - 1) / max(1, n - 1)) for i in range(n)]
    schedule = []
    for idx in indices:
        ep = epochs[idx]
        schedule.append((ep.suggested_xshrf, ep.suggested_yshrf))

    while len(schedule) < base_iters:
        schedule.append(schedule[-1])

    return schedule[:base_iters]


def weighted_shrink(ca_result: CARunResult) -> Tuple[float, float]:
    """Compute convergence-weighted average of suggested shrink factors."""
    epochs = ca_result.epoch_results
    if not epochs:
        return 0.9, 0.9
    # Weight later epochs more heavily
    weights = np.linspace(0.5, 1.0, len(epochs))
    xs = np.array([e.suggested_xshrf for e in epochs])
    ys = np.array([e.suggested_yshrf for e in epochs])
    xshrf = float(np.average(xs, weights=weights))
    yshrf = float(np.average(ys, weights=weights))
    return round(xshrf, 4), round(yshrf, 4)
