"""
Shrink factor planner: derives Xshrf and Yshrf from Rule-110 pressure signals.
"""

import numpy as np
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def plan_shrink_factors(
    run_result,
    occupancy_ratio: float,
    base_xshrf: float = 0.9,
    base_yshrf: float = 0.9,
) -> Tuple[float, float]:
    """
    Compute final Xshrf and Yshrf recommendations.

    High occupancy → conservative shrink (closer to 1.0)
    Strong CA pressure → more aggressive shrink in that direction

    Compatible with both Rule110RunResult and legacy CARunResult.
    """
    from .directional_pressure import weighted_shrink
    ca_xshrf, ca_yshrf = weighted_shrink(run_result)

    conservatism = float(np.clip(occupancy_ratio, 0.0, 1.0))
    xshrf = ca_xshrf * (1.0 - 0.2 * conservatism) + base_xshrf * 0.2 * conservatism
    yshrf = ca_yshrf * (1.0 - 0.2 * conservatism) + base_yshrf * 0.2 * conservatism

    xshrf = float(np.clip(xshrf, 0.70, 0.99))
    yshrf = float(np.clip(yshrf, 0.70, 0.99))

    logger.debug(
        "ShrinkPlanner: occ=%.2f ca=(%.3f,%.3f) final=(%.3f,%.3f)",
        occupancy_ratio, ca_xshrf, ca_yshrf, xshrf, yshrf,
    )
    return round(xshrf, 4), round(yshrf, 4)
