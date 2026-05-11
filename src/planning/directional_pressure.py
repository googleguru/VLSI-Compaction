"""
Directional pressure extractor.

Works with both the Rule-110 scheduler (Rule110RunResult) and the legacy
7-rule composite scheduler (CARunResult) so both flows share the same
planning interface.
"""

import numpy as np
import logging
from typing import List, Tuple, Union

logger = logging.getLogger(__name__)

# Accept either result type
_AnyRunResult = object


def extract_dominant_direction(run_result: _AnyRunResult) -> str:
    """Return 'x', 'y', or 'both' based on net CA pressure."""
    epochs = getattr(run_result, "epoch_results", [])
    if not epochs:
        return "both"

    last = epochs[-1]

    # Rule110EpochResult has col_pressure / row_pressure
    if hasattr(last, "col_pressure") and hasattr(last, "row_pressure"):
        xp = float(np.array(last.col_pressure).mean())
        yp = float(np.array(last.row_pressure).mean())
    else:
        # Legacy CARunResult
        pres = last.aggregate_pressure
        xp = abs(pres.get("net_xp", 0.0))
        yp = abs(pres.get("net_yp", 0.0))

    if xp > 2 * yp:
        return "x"
    if yp > 2 * xp:
        return "y"
    return "both"


def derive_iteration_schedule(
    run_result: _AnyRunResult,
    base_iters: int = 5,
) -> List[Tuple[float, float]]:
    """Return [(xshrf, yshrf)] for each planned backend iteration."""
    epochs = getattr(run_result, "epoch_results", [])
    if not epochs:
        return [(0.9, 0.9)] * base_iters

    n       = min(base_iters, len(epochs))
    indices = [int(i * (len(epochs) - 1) / max(1, n - 1)) for i in range(n)]
    schedule = [(epochs[i].suggested_xshrf, epochs[i].suggested_yshrf) for i in indices]

    while len(schedule) < base_iters:
        schedule.append(schedule[-1])
    return schedule[:base_iters]


def weighted_shrink(run_result: _AnyRunResult) -> Tuple[float, float]:
    """Convergence-weighted average of suggested shrink factors."""
    epochs = getattr(run_result, "epoch_results", [])
    if not epochs:
        return 0.9, 0.9
    weights = np.linspace(0.5, 1.0, len(epochs))
    xs = np.array([e.suggested_xshrf for e in epochs])
    ys = np.array([e.suggested_yshrf for e in epochs])
    xshrf = float(np.average(xs, weights=weights))
    yshrf = float(np.average(ys, weights=weights))
    return round(xshrf, 4), round(yshrf, 4)


def pressure_map_from_result(run_result: _AnyRunResult) -> np.ndarray:
    """
    Return the final 2-D pressure map.
    Rule110RunResult has a fused map; legacy result synthesizes one from
    scalar pressure aggregates.
    """
    final_map = getattr(run_result, "final_pressure_map", None)
    if final_map is not None:
        return final_map

    # Legacy: no 2-D map; return empty array
    return np.zeros((1, 1), dtype=np.float32)
