"""
CA epoch scheduler.
Drives the CA iteration loop, extracts per-epoch compaction hints,
and detects global convergence.
"""

import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from .state_encoder import (
    init_state, compute_aggregate_pressure,
    F_ELIGIBLE, F_XPRESSURE, F_YPRESSURE, F_CONFLICT,
)
from .rule_engine import RULE_REGISTRY

logger = logging.getLogger(__name__)


@dataclass
class EpochResult:
    epoch: int
    state: np.ndarray
    aggregate_pressure: dict
    suggested_xshrf: float
    suggested_yshrf: float
    active_fraction: float
    converged: bool


@dataclass
class CARunResult:
    epoch_results: List[EpochResult] = field(default_factory=list)
    final_xshrf: float = 0.9
    final_yshrf: float = 0.9
    converged: bool = False
    epochs_run: int = 0

    def pressure_history(self) -> Tuple[List[float], List[float]]:
        xp = [e.aggregate_pressure["mean_xp"] for e in self.epoch_results]
        yp = [e.aggregate_pressure["mean_yp"] for e in self.epoch_results]
        return xp, yp


class EpochScheduler:
    def __init__(
        self,
        rules_config: Dict[str, Any],
        enabled_rules: List[str],
        max_epochs: int = 20,
        convergence_threshold: float = 0.01,
        neighborhood: str = "moore",
    ):
        self.rules_config  = rules_config
        self.enabled_rules = enabled_rules
        self.max_epochs    = max_epochs
        self.conv_threshold = convergence_threshold
        self.neighborhood  = neighborhood

    def run(self, occupancy_grid: np.ndarray) -> CARunResult:
        state = init_state(occupancy_grid)
        result = CARunResult()
        prev_state: Optional[np.ndarray] = None

        for epoch in range(self.max_epochs):
            state, epoch_result = self._step(state, epoch, prev_state)
            result.epoch_results.append(epoch_result)

            logger.debug(
                "Epoch %02d: active=%.3f xshrf=%.3f yshrf=%.3f converged=%s",
                epoch,
                epoch_result.active_fraction,
                epoch_result.suggested_xshrf,
                epoch_result.suggested_yshrf,
                epoch_result.converged,
            )

            if epoch_result.converged:
                result.converged = True
                result.epochs_run = epoch + 1
                break

            prev_state = state.copy()

        if not result.converged:
            result.epochs_run = self.max_epochs

        if result.epoch_results:
            last = result.epoch_results[-1]
            result.final_xshrf = last.suggested_xshrf
            result.final_yshrf = last.suggested_yshrf

        return result

    def _step(
        self,
        state: np.ndarray,
        epoch: int,
        prev_state: Optional[np.ndarray],
    ) -> Tuple[np.ndarray, EpochResult]:
        new_state = state

        for rule_name in self.enabled_rules:
            fn = RULE_REGISTRY.get(rule_name)
            if fn is None:
                logger.warning("Unknown rule: %s", rule_name)
                continue
            rule_cfg = dict(self.rules_config.get(rule_name, {}))
            if rule_name == "stabilization" and prev_state is not None:
                rule_cfg["prev_state"] = prev_state
            new_state = fn(new_state, epoch, rule_cfg)

        pressure = compute_aggregate_pressure(new_state)
        xshrf, yshrf = self._suggest_shrink(new_state, pressure)
        active_fraction = self._active_fraction(new_state)
        converged = self._check_convergence(state, new_state)

        epoch_result = EpochResult(
            epoch=epoch,
            state=new_state,
            aggregate_pressure=pressure,
            suggested_xshrf=xshrf,
            suggested_yshrf=yshrf,
            active_fraction=active_fraction,
            converged=converged,
        )
        return new_state, epoch_result

    def _suggest_shrink(self, state: np.ndarray, pressure: dict) -> Tuple[float, float]:
        cfg = self.rules_config.get("shrink_adaptation", {})
        min_s = cfg.get("min_shrink", 0.80)
        max_s = cfg.get("max_shrink", 0.99)
        scale = cfg.get("congestion_scale", 0.10)

        mean_conflict = float(np.mean(state[:, :, F_CONFLICT]))
        xp_mag = pressure.get("mean_xp", 0.0)
        yp_mag = pressure.get("mean_yp", 0.0)

        xshrf = float(np.clip(max_s - xp_mag * scale - mean_conflict * 0.05, min_s, max_s))
        yshrf = float(np.clip(max_s - yp_mag * scale - mean_conflict * 0.05, min_s, max_s))
        return xshrf, yshrf

    def _active_fraction(self, state: np.ndarray) -> float:
        occ = (state[:, :, 0] == 1).sum()
        if occ == 0:
            return 0.0
        eligible = (state[:, :, F_ELIGIBLE] > 0.5).sum()
        return float(eligible) / float(occ)

    def _check_convergence(
        self, old: np.ndarray, new: np.ndarray
    ) -> bool:
        delta = np.abs(new[:, :, F_XPRESSURE] - old[:, :, F_XPRESSURE]).mean()
        delta += np.abs(new[:, :, F_YPRESSURE] - old[:, :, F_YPRESSURE]).mean()
        return float(delta) < self.conv_threshold
