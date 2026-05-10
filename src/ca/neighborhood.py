"""
Neighborhood operators for the 2D CA.
Supports von Neumann (4-connected) and Moore (8-connected) topologies.
"""

import numpy as np
from typing import Tuple


def vonneumann_neighbors(
    grid: np.ndarray, r: int, c: int
) -> np.ndarray:
    """Return the 4 von Neumann neighbors (with zero-padding at borders)."""
    rows, cols = grid.shape[:2]
    neighbors = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            neighbors.append(grid[nr, nc])
        else:
            neighbors.append(np.zeros_like(grid[0, 0]))
    return np.stack(neighbors, axis=0)


def moore_neighbors(
    grid: np.ndarray, r: int, c: int
) -> np.ndarray:
    """Return all 8 Moore neighbors (with zero-padding at borders)."""
    rows, cols = grid.shape[:2]
    neighbors = []
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                neighbors.append(grid[nr, nc])
            else:
                neighbors.append(np.zeros_like(grid[0, 0]))
    return np.stack(neighbors, axis=0)


def neighborhood_free_space_gradient(
    state: np.ndarray, r: int, c: int
) -> Tuple[float, float]:
    """
    Compute (dx, dy) gradient of free-space field using finite differences.
    Positive x = right direction has more free space.
    """
    from .state_encoder import F_FREESPACE
    rows, cols = state.shape[:2]

    def fs(rr, cc):
        if 0 <= rr < rows and 0 <= cc < cols:
            return float(state[rr, cc, F_FREESPACE])
        return 0.0

    dx = fs(r, c + 1) - fs(r, c - 1)
    dy = fs(r + 1, c) - fs(r - 1, c)
    return dx, dy


def compute_free_space_map(state: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """
    Compute local free-space score for each cell using a sliding-window mean.
    """
    from scipy.ndimage import uniform_filter
    from .state_encoder import F_FREESPACE, F_OCCUPANCY
    empty_mask = (state[:, :, F_OCCUPANCY] == 0).astype(np.float32)
    smoothed = uniform_filter(empty_mask, size=kernel_size, mode='constant', cval=0.0)
    return smoothed


def compute_conflict_map(state: np.ndarray, kernel_size: int = 3) -> np.ndarray:
    """
    Compute local conflict density (occupied neighbor fraction) per cell.
    """
    from scipy.ndimage import uniform_filter
    from .state_encoder import F_OCCUPANCY
    occ_mask = (state[:, :, F_OCCUPANCY] == 1).astype(np.float32)
    smoothed = uniform_filter(occ_mask, size=kernel_size, mode='constant', cval=0.0)
    return smoothed
