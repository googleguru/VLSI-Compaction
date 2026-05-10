"""
Multi-field CA state encoding.
Each cell stores: occupancy, x_pressure, y_pressure, conflict_density,
free_space_score, mobility, compaction_eligible.
"""

import numpy as np
from dataclasses import dataclass

# Field indices into the state tensor (last axis)
F_OCCUPANCY   = 0
F_XPRESSURE   = 1
F_YPRESSURE   = 2
F_CONFLICT    = 3
F_FREESPACE   = 4
F_MOBILITY    = 5
F_ELIGIBLE    = 6

N_FIELDS = 7


@dataclass
class StateField:
    OCCUPANCY  = F_OCCUPANCY
    XPRESSURE  = F_XPRESSURE
    YPRESSURE  = F_YPRESSURE
    CONFLICT   = F_CONFLICT
    FREESPACE  = F_FREESPACE
    MOBILITY   = F_MOBILITY
    ELIGIBLE   = F_ELIGIBLE


def init_state(occupancy_grid: np.ndarray) -> np.ndarray:
    """
    Build initial CA state tensor from an occupancy grid.
    Returns shape (rows, cols, N_FIELDS).
    """
    rows, cols = occupancy_grid.shape
    state = np.zeros((rows, cols, N_FIELDS), dtype=np.float32)

    state[:, :, F_OCCUPANCY] = occupancy_grid.astype(np.float32)

    # Seed free-space from occupancy
    occupied = (occupancy_grid == 1)
    empty    = (occupancy_grid == 0)
    state[empty,    F_FREESPACE] = 1.0
    state[occupied, F_FREESPACE] = 0.0

    # All geometry cells are initially eligible
    state[occupied, F_ELIGIBLE] = 1.0

    # Boundary cells are not eligible
    boundary = (occupancy_grid == 3)
    state[boundary, F_ELIGIBLE]  = 0.0
    state[boundary, F_OCCUPANCY] = 3.0

    # Initial mobility based on local free space (will be updated by rules)
    state[occupied, F_MOBILITY] = 0.5

    return state


def extract_pressure_fields(state: np.ndarray):
    """Return (xp, yp) pressure arrays shaped (rows, cols)."""
    return state[:, :, F_XPRESSURE], state[:, :, F_YPRESSURE]


def compute_aggregate_pressure(state: np.ndarray) -> dict:
    xp = state[:, :, F_XPRESSURE]
    yp = state[:, :, F_YPRESSURE]
    eligible = state[:, :, F_ELIGIBLE] > 0.5
    if eligible.sum() == 0:
        return {"mean_xp": 0.0, "mean_yp": 0.0, "net_xp": 0.0, "net_yp": 0.0}
    return {
        "mean_xp": float(np.mean(np.abs(xp[eligible]))),
        "mean_yp": float(np.mean(np.abs(yp[eligible]))),
        "net_xp":  float(np.mean(xp[eligible])),
        "net_yp":  float(np.mean(yp[eligible])),
    }
