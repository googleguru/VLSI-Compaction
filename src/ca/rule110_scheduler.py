"""
Rule-110 epoch scheduler for 2-D layout compaction planning.

The scheduler lifts the 1-D Rule 110 automaton into 2-D by running
alternating horizontal (row) and vertical (column) passes.  A damping
coefficient prevents oscillation and ensures eventual stabilization.

Pass ordering:
  epoch 0   → row pass  (horizontal pressure)
  epoch 1   → col pass  (vertical pressure)
  epoch 2   → row pass  …
  (configurable; can be row-only, col-only, or alternating)

Output: per-epoch row_pressure, col_pressure, fused pressure map, and
suggested compaction shrink factors derived from the pressure fields.
"""

import numpy as np
import logging
from dataclasses import dataclass, field
from typing import List, Literal, Tuple, Optional

from .rule110 import (
    apply_rule110_rows,
    apply_rule110_cols,
    row_activity,
    col_activity,
    fuse_pressure,
)

logger = logging.getLogger(__name__)

_PassMode = Literal["alternating", "row_only", "col_only"]


@dataclass
class Rule110EpochResult:
    epoch: int
    pass_type: str                 # 'row' | 'col'
    state: np.ndarray              # current binary grid (float32)
    row_pressure: np.ndarray       # per-row mean activity
    col_pressure: np.ndarray       # per-col mean activity
    pressure_map: np.ndarray       # fused 2-D pressure field
    suggested_xshrf: float
    suggested_yshrf: float
    active_fraction: float         # fraction of cells that are 1


@dataclass
class Rule110RunResult:
    epoch_results: List[Rule110EpochResult] = field(default_factory=list)
    final_xshrf: float = 0.9
    final_yshrf: float = 0.9
    final_pressure_map: Optional[np.ndarray] = None
    epochs_run: int = 0

    def pressure_history(self) -> Tuple[List[float], List[float]]:
        """Return (mean_x_pressure, mean_y_pressure) per epoch."""
        xp = [float(e.col_pressure.mean()) for e in self.epoch_results]
        yp = [float(e.row_pressure.mean()) for e in self.epoch_results]
        return xp, yp

    def shrink_history(self) -> Tuple[List[float], List[float]]:
        xs = [e.suggested_xshrf for e in self.epoch_results]
        ys = [e.suggested_yshrf for e in self.epoch_results]
        return xs, ys


class Rule110Scheduler:
    """
    Run alternating Rule-110 row/column passes over an occupancy grid and
    extract compaction pressure signals.

    Parameters
    ----------
    max_epochs : int
        Total number of CA passes (each pass = one epoch).
    boundary : 'clamped' | 'periodic'
        Boundary condition for Rule 110 updates.
    damping : float in (0, 1]
        New state = damping * rule110_output + (1-damping) * old_state.
        Prevents oscillation; 1.0 = no damping (pure Rule 110).
    mode : 'alternating' | 'row_only' | 'col_only'
        Which passes to run.
    min_shrink : float
        Minimum allowed shrink factor.
    max_shrink : float
        Maximum allowed shrink factor.
    seed : int
        Not used for CA (deterministic), exposed for reproducibility.
    """

    def __init__(
        self,
        max_epochs: int = 20,
        boundary: Literal["clamped", "periodic"] = "clamped",
        damping: float = 0.85,
        mode: _PassMode = "alternating",
        min_shrink: float = 0.80,
        max_shrink: float = 0.99,
        seed: int = 42,
    ):
        self.max_epochs = max_epochs
        self.boundary   = boundary
        self.damping    = float(np.clip(damping, 1e-6, 1.0))
        self.mode       = mode
        self.min_shrink = min_shrink
        self.max_shrink = max_shrink
        self.seed       = seed

    def run(self, occupancy_grid: np.ndarray) -> Rule110RunResult:
        """
        Run the scheduler on a binary occupancy grid.

        Parameters
        ----------
        occupancy_grid : 2-D array (H × W), values 0 or 1 (or float)
        """
        state = (occupancy_grid > 0.5).astype(np.float32)
        result = Rule110RunResult()

        for epoch in range(self.max_epochs):
            pass_type = self._pass_type(epoch)
            state, er = self._step(state, epoch, pass_type)
            result.epoch_results.append(er)

            logger.debug(
                "Rule110 epoch %02d [%s]: active=%.3f xshrf=%.3f yshrf=%.3f",
                epoch, pass_type, er.active_fraction,
                er.suggested_xshrf, er.suggested_yshrf,
            )

        result.epochs_run = self.max_epochs
        if result.epoch_results:
            last = result.epoch_results[-1]
            result.final_xshrf       = last.suggested_xshrf
            result.final_yshrf       = last.suggested_yshrf
            result.final_pressure_map = last.pressure_map

        return result

    # ── private ───────────────────────────────────────────────────────────────

    def _pass_type(self, epoch: int) -> str:
        if self.mode == "row_only":
            return "row"
        if self.mode == "col_only":
            return "col"
        return "row" if epoch % 2 == 0 else "col"

    def _step(
        self, state: np.ndarray, epoch: int, pass_type: str
    ) -> Tuple[np.ndarray, Rule110EpochResult]:
        binary = (state > 0.5).astype(np.uint8)

        if pass_type == "row":
            updated = apply_rule110_rows(binary, self.boundary).astype(np.float32)
        else:
            updated = apply_rule110_cols(binary, self.boundary).astype(np.float32)

        # Damped update: blend new rule output with previous state
        new_state = self.damping * updated + (1.0 - self.damping) * state

        row_pres = row_activity(new_state)
        col_pres = col_activity(new_state)
        pmap     = fuse_pressure(row_pres, col_pres, new_state.shape)

        xshrf, yshrf = self._suggest_shrink(col_pres, row_pres)
        active_frac  = float(new_state.mean())

        er = Rule110EpochResult(
            epoch          = epoch,
            pass_type      = pass_type,
            state          = new_state,
            row_pressure   = row_pres,
            col_pressure   = col_pres,
            pressure_map   = pmap,
            suggested_xshrf = xshrf,
            suggested_yshrf = yshrf,
            active_fraction = active_frac,
        )
        return new_state, er

    def _suggest_shrink(
        self,
        col_pres: np.ndarray,
        row_pres: np.ndarray,
    ) -> Tuple[float, float]:
        """
        Derive shrink factors from pressure magnitudes.
        Higher pressure → more aggressive shrink (lower shrink factor).
        """
        xp = float(col_pres.mean())  # column activity → x-axis pressure
        yp = float(row_pres.mean())  # row activity    → y-axis pressure

        # Map pressure [0, 1] → shrink [max_shrink, min_shrink]
        span   = self.max_shrink - self.min_shrink
        xshrf  = float(np.clip(self.max_shrink - xp * span, self.min_shrink, self.max_shrink))
        yshrf  = float(np.clip(self.max_shrink - yp * span, self.min_shrink, self.max_shrink))
        return round(xshrf, 4), round(yshrf, 4)
