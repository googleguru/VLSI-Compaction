"""
CA rule engine: applies individual rules to evolve the state tensor.

All rule functions accept a `neighborhood` key in `cfg` (default "moore")
so the epoch scheduler can switch between Moore (8-connected) and von Neumann
(4-connected) topologies without changing rule logic.
"""

import numpy as np
import logging
from typing import Dict, Any, Callable

from .state_encoder import (
    F_OCCUPANCY, F_XPRESSURE, F_YPRESSURE, F_CONFLICT,
    F_FREESPACE, F_MOBILITY, F_ELIGIBLE, N_FIELDS,
)
from .neighborhood import (
    compute_free_space_map, compute_conflict_map, smooth_field,
)

logger = logging.getLogger(__name__)

RuleFn = Callable[[np.ndarray, int, Dict[str, Any]], np.ndarray]


def rule_free_space_attraction(
    state: np.ndarray, epoch: int, cfg: Dict[str, Any]
) -> np.ndarray:
    """
    Increase pressure toward directions with more free space.
    Uses the neighborhood topology from cfg["neighborhood"] to compute
    the free-space density map, then derives a gradient via finite differences.
    """
    threshold = cfg.get("free_space_threshold", 0.3)
    inc       = cfg.get("pressure_increment",   0.15)
    nb        = cfg.get("neighborhood", "moore")

    fs_map    = compute_free_space_map(state, neighborhood=nb)
    new_state = state.copy()
    eligible  = (state[:, :, F_ELIGIBLE] > 0.5) & (state[:, :, F_OCCUPANCY] == 1)

    # Vectorized gradient: forward/backward finite differences
    fs_right = np.roll(fs_map, -1, axis=1)
    fs_left  = np.roll(fs_map,  1, axis=1)
    fs_up    = np.roll(fs_map, -1, axis=0)
    fs_down  = np.roll(fs_map,  1, axis=0)

    dx = fs_right - fs_left
    dy = fs_up    - fs_down

    # Zero out wrap-around border artefacts
    dx[:, 0]  = 0.0;  dx[:, -1] = 0.0
    dy[0, :]  = 0.0;  dy[-1, :] = 0.0

    mask = eligible & (fs_map > threshold)
    new_state[mask, F_XPRESSURE] = np.clip(
        state[mask, F_XPRESSURE] + inc * dx[mask], -1.0, 1.0
    )
    new_state[mask, F_YPRESSURE] = np.clip(
        state[mask, F_YPRESSURE] + inc * dy[mask], -1.0, 1.0
    )
    return new_state


def rule_conflict_repulsion(
    state: np.ndarray, epoch: int, cfg: Dict[str, Any]
) -> np.ndarray:
    """
    Reduce movement pressure when local conflict density is high.
    Conflict density is measured using the configured neighborhood topology.
    """
    threshold = cfg.get("conflict_threshold",  0.5)
    strength  = cfg.get("repulsion_strength",  0.20)
    nb        = cfg.get("neighborhood", "moore")

    conflict_map = compute_conflict_map(state, neighborhood=nb)
    new_state    = state.copy()

    high_conflict = conflict_map > threshold
    occ           = state[:, :, F_OCCUPANCY] == 1
    mask          = high_conflict & occ

    new_state[mask, F_XPRESSURE] = np.clip(
        state[mask, F_XPRESSURE] * (1.0 - strength), -1.0, 1.0
    )
    new_state[mask, F_YPRESSURE] = np.clip(
        state[mask, F_YPRESSURE] * (1.0 - strength), -1.0, 1.0
    )
    new_state[mask, F_CONFLICT] = conflict_map[mask]
    return new_state


def rule_connectivity_preservation(
    state: np.ndarray, epoch: int, cfg: Dict[str, Any]
) -> np.ndarray:
    """
    Cells with occupied neighbors receive a directional bias aligned with
    the neighborhood-average pressure to reduce topological fragmentation.
    Smoothing uses the configured neighborhood kernel.
    """
    bias = cfg.get("bias_strength", 0.10)
    nb   = cfg.get("neighborhood", "moore")

    xp = state[:, :, F_XPRESSURE]
    yp = state[:, :, F_YPRESSURE]
    occ = state[:, :, F_OCCUPANCY] == 1

    mean_xp = smooth_field(xp, neighborhood=nb)
    mean_yp = smooth_field(yp, neighborhood=nb)

    new_state = state.copy()
    new_state[occ, F_XPRESSURE] = np.clip(
        state[occ, F_XPRESSURE] + bias * mean_xp[occ], -1.0, 1.0
    )
    new_state[occ, F_YPRESSURE] = np.clip(
        state[occ, F_YPRESSURE] + bias * mean_yp[occ], -1.0, 1.0
    )
    return new_state


def rule_boundary_guard(
    state: np.ndarray, epoch: int, cfg: Dict[str, Any]
) -> np.ndarray:
    """
    Zero out boundary-facing pressure components within `guard_margin` cells
    of the layout outline. Topology-independent.
    """
    margin = cfg.get("guard_margin", 1)
    rows, cols = state.shape[:2]
    new_state = state.copy()

    # Left: disallow leftward motion (xp < 0)
    new_state[:, :margin, F_XPRESSURE] = np.maximum(
        state[:, :margin, F_XPRESSURE], 0.0
    )
    # Right: disallow rightward motion (xp > 0)
    new_state[:, cols - margin:, F_XPRESSURE] = np.minimum(
        state[:, cols - margin:, F_XPRESSURE], 0.0
    )
    # Bottom: disallow downward motion (yp < 0)
    new_state[:margin, :, F_YPRESSURE] = np.maximum(
        state[:margin, :, F_YPRESSURE], 0.0
    )
    # Top: disallow upward motion (yp > 0)
    new_state[rows - margin:, :, F_YPRESSURE] = np.minimum(
        state[rows - margin:, :, F_YPRESSURE], 0.0
    )
    return new_state


def rule_alternating_axis_schedule(
    state: np.ndarray, epoch: int, cfg: Dict[str, Any]
) -> np.ndarray:
    """
    On even epochs emphasize X-axis pressure; on odd epochs emphasize Y-axis.
    Matches the backend's alternating horizontal/vertical compaction style.
    Topology-independent.
    """
    x_epochs = set(cfg.get("x_epochs", list(range(0, 20, 2))))
    y_epochs = set(cfg.get("y_epochs", list(range(1, 20, 2))))
    new_state = state.copy()

    if epoch in x_epochs:
        new_state[:, :, F_YPRESSURE] *= 0.5
    elif epoch in y_epochs:
        new_state[:, :, F_XPRESSURE] *= 0.5

    return new_state


def rule_shrink_adaptation(
    state: np.ndarray, epoch: int, cfg: Dict[str, Any]
) -> np.ndarray:
    """
    Stores per-cell conflict density in F_CONFLICT for use by the epoch
    scheduler's shrink-factor derivation. Uses the neighborhood kernel.
    """
    nb = cfg.get("neighborhood", "moore")
    conflict_map = compute_conflict_map(state, neighborhood=nb)
    new_state = state.copy()
    new_state[:, :, F_CONFLICT] = conflict_map
    return new_state


def rule_stabilization(
    state: np.ndarray, epoch: int, cfg: Dict[str, Any]
) -> np.ndarray:
    """
    Mark cells as ineligible when their (xp, yp) change vs the previous epoch
    falls below `stable_threshold`. Reduces oscillation in converged regions.
    Topology-independent.
    """
    threshold = cfg.get("stable_threshold", 0.005)
    prev = cfg.get("prev_state")
    if prev is None:
        return state

    new_state = state.copy()
    delta_xp  = np.abs(state[:, :, F_XPRESSURE] - prev[:, :, F_XPRESSURE])
    delta_yp  = np.abs(state[:, :, F_YPRESSURE] - prev[:, :, F_YPRESSURE])
    converged = (delta_xp < threshold) & (delta_yp < threshold)
    occ       = state[:, :, F_OCCUPANCY] == 1
    new_state[occ & converged, F_ELIGIBLE] = 0.0
    return new_state


RULE_REGISTRY: Dict[str, RuleFn] = {
    "free_space_attraction":     rule_free_space_attraction,
    "conflict_repulsion":        rule_conflict_repulsion,
    "connectivity_preservation": rule_connectivity_preservation,
    "boundary_guard":            rule_boundary_guard,
    "alternating_axis_schedule": rule_alternating_axis_schedule,
    "shrink_adaptation":         rule_shrink_adaptation,
    "stabilization":             rule_stabilization,
}
