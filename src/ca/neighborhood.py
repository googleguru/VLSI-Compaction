"""
Neighborhood operators for the 2D CA.
Supports von Neumann (4-connected) and Moore (8-connected) topologies.
All vectorized map functions accept a `neighborhood` parameter so the
epoch scheduler can switch topologies without changing rule code.
"""

import numpy as np
from typing import Tuple


# ── per-cell helpers (used for reference / testing) ──────────────────────────

def vonneumann_neighbors(grid: np.ndarray, r: int, c: int) -> np.ndarray:
    """Return the 4 von Neumann neighbors (zero-padded at borders)."""
    rows, cols = grid.shape[:2]
    neighbors = []
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            neighbors.append(grid[nr, nc])
        else:
            neighbors.append(np.zeros_like(grid[0, 0]))
    return np.stack(neighbors, axis=0)


def moore_neighbors(grid: np.ndarray, r: int, c: int) -> np.ndarray:
    """Return all 8 Moore neighbors (zero-padded at borders)."""
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


# ── vectorized kernel selection ───────────────────────────────────────────────

def get_neighborhood_kernel(neighborhood: str) -> np.ndarray:
    """
    Return a normalized 3×3 convolution kernel for the requested topology.

    Moore (8-connected):      Von Neumann (4-connected):
      1 1 1                     0 1 0
      1 1 1   / 9               1 1 1   / 5
      1 1 1                     0 1 0
    """
    if neighborhood == "vonneumann":
        k = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.float32)
        return k / k.sum()
    # Default: Moore 8-connected
    return np.ones((3, 3), dtype=np.float32) / 9.0


# ── vectorized map functions ──────────────────────────────────────────────────

def compute_free_space_map(
    state: np.ndarray, neighborhood: str = "moore"
) -> np.ndarray:
    """
    Compute local free-space score for each cell via neighborhood-weighted mean.
    Returns array shaped (rows, cols) with values in [0, 1].
    """
    from scipy.ndimage import convolve
    from .state_encoder import F_OCCUPANCY
    kernel = get_neighborhood_kernel(neighborhood)
    empty_mask = (state[:, :, F_OCCUPANCY] == 0).astype(np.float32)
    return convolve(empty_mask, kernel, mode="constant", cval=0.0)


def compute_conflict_map(
    state: np.ndarray, neighborhood: str = "moore"
) -> np.ndarray:
    """
    Compute local conflict density (occupied neighbor fraction) per cell.
    Returns array shaped (rows, cols) with values in [0, 1].
    """
    from scipy.ndimage import convolve
    from .state_encoder import F_OCCUPANCY
    kernel = get_neighborhood_kernel(neighborhood)
    occ_mask = (state[:, :, F_OCCUPANCY] == 1).astype(np.float32)
    return convolve(occ_mask, kernel, mode="constant", cval=0.0)


def smooth_field(
    field: np.ndarray, neighborhood: str = "moore"
) -> np.ndarray:
    """Smooth an arbitrary 2D float field with the neighborhood kernel."""
    from scipy.ndimage import convolve
    kernel = get_neighborhood_kernel(neighborhood)
    return convolve(field.astype(np.float32), kernel, mode="constant", cval=0.0)
