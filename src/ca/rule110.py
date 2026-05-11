"""
Rule 110 elementary cellular automaton.

Rule 110 truth table (Wolfram code 110 = 0b01101110):
  neighborhood (L,C,R) -> next state
  (1,1,1) -> 0
  (1,1,0) -> 1
  (1,0,1) -> 1
  (1,0,0) -> 0
  (0,1,1) -> 1
  (0,1,0) -> 1
  (0,0,1) -> 1
  (0,0,0) -> 0

Rule 110 sits at the boundary of order and chaos (Wolfram Class IV),
exhibits complex emergent behaviour, and is known to be computationally
universal — properties that make it well-suited as a pressure-propagation
rule for VLSI layout compaction planning.

2-D lift: alternating horizontal row passes and vertical column passes.
"""

import numpy as np
from typing import Literal

# Precomputed lookup table indexed by 3-bit neighbourhood 4L+2C+R
_RULE110 = np.array([0, 1, 1, 1, 0, 1, 1, 0], dtype=np.uint8)


def apply_rule110_1d(
    row: np.ndarray,
    boundary: Literal["clamped", "periodic"] = "clamped",
) -> np.ndarray:
    """
    Apply one step of Rule 110 to a 1-D binary array.

    Parameters
    ----------
    row : 1-D array, values treated as binary (>0.5 → 1)
    boundary : 'clamped' pads with 0; 'periodic' wraps around

    Returns
    -------
    next_row : np.ndarray of dtype uint8, same length as input
    """
    cells = (row > 0.5).astype(np.uint8)
    n = len(cells)
    if boundary == "periodic":
        left  = np.roll(cells,  1)
        right = np.roll(cells, -1)
    else:
        left  = np.empty(n, dtype=np.uint8)
        right = np.empty(n, dtype=np.uint8)
        left[0]    = 0
        left[1:]   = cells[:-1]
        right[-1]  = 0
        right[:-1] = cells[1:]
    idx = (left << 2) | (cells << 1) | right
    return _RULE110[idx]


def apply_rule110_rows(
    grid: np.ndarray,
    boundary: Literal["clamped", "periodic"] = "clamped",
) -> np.ndarray:
    """Apply Rule 110 to every row of a 2-D grid independently."""
    out = np.empty_like(grid, dtype=np.uint8)
    for r in range(grid.shape[0]):
        out[r] = apply_rule110_1d(grid[r], boundary)
    return out


def apply_rule110_cols(
    grid: np.ndarray,
    boundary: Literal["clamped", "periodic"] = "clamped",
) -> np.ndarray:
    """Apply Rule 110 to every column of a 2-D grid independently."""
    out = np.empty_like(grid, dtype=np.uint8)
    for c in range(grid.shape[1]):
        out[:, c] = apply_rule110_1d(grid[:, c], boundary)
    return out


def row_activity(grid: np.ndarray) -> np.ndarray:
    """Return per-row mean activation (float32, length = grid.shape[0])."""
    return grid.astype(np.float32).mean(axis=1)


def col_activity(grid: np.ndarray) -> np.ndarray:
    """Return per-column mean activation (float32, length = grid.shape[1])."""
    return grid.astype(np.float32).mean(axis=0)


def fuse_pressure(
    row_act: np.ndarray,
    col_act: np.ndarray,
    grid_shape: tuple,
) -> np.ndarray:
    """
    Build a 2-D pressure map by broadcasting row and column activity vectors.
    Returns a float32 array of shape grid_shape.
    """
    H, W = grid_shape
    row_map = np.broadcast_to(row_act[:, np.newaxis], (H, W)).astype(np.float32)
    col_map = np.broadcast_to(col_act[np.newaxis, :], (H, W)).astype(np.float32)
    return (row_map + col_map) * 0.5
