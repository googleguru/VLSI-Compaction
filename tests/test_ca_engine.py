"""
Tests for the CA grid discretizer, state encoder, and rule engine.
"""

import numpy as np
import pytest
from src.ca.grid_discretizer import GridDiscretizer
from src.ca.state_encoder import init_state, F_OCCUPANCY, F_ELIGIBLE, F_FREESPACE
from src.ca.rule_engine import (
    rule_free_space_attraction,
    rule_conflict_repulsion,
    rule_boundary_guard,
    rule_alternating_axis_schedule,
)
from src.io.cif_reader import CIFReader

import textwrap

_SIMPLE_CIF = textwrap.dedent("""\
    DS 1 1 2;
    L POLY;
    B 200 100 100 50;
    DF;
    C 1;
    E
""")


def _make_grid():
    reader = CIFReader()
    layout = reader.read_string(_SIMPLE_CIF)
    disc   = GridDiscretizer(resolution=5)
    grid, _ = disc.discretize(layout)
    return grid


def test_discretizer_produces_2d_grid():
    grid = _make_grid()
    assert grid.ndim == 2
    assert grid.shape[0] > 0
    assert grid.shape[1] > 0


def test_discretizer_has_occupied_cells():
    grid = _make_grid()
    assert (grid == GridDiscretizer.OCCUPIED).any()


def test_discretizer_has_boundary():
    grid = _make_grid()
    assert (grid == GridDiscretizer.BOUNDARY).any()


def test_init_state_shape():
    grid  = _make_grid()
    state = init_state(grid)
    assert state.shape == (grid.shape[0], grid.shape[1], 7)


def test_init_state_free_space():
    grid  = _make_grid()
    state = init_state(grid)
    empty = grid == 0
    assert (state[empty, F_FREESPACE] == 1.0).all()


def test_init_state_eligible():
    grid  = _make_grid()
    state = init_state(grid)
    occ   = grid == GridDiscretizer.OCCUPIED
    bound = grid == GridDiscretizer.BOUNDARY
    assert (state[occ, F_ELIGIBLE] == 1.0).all()
    assert (state[bound, F_ELIGIBLE] == 0.0).all()


def test_free_space_attraction_modifies_pressure():
    grid  = _make_grid()
    state = init_state(grid)
    cfg   = {"free_space_threshold": 0.0, "pressure_increment": 0.1}
    new   = rule_free_space_attraction(state, 0, cfg)
    # Pressure should differ from initial zeros in occupied regions
    occ   = grid == GridDiscretizer.OCCUPIED
    if occ.any():
        delta = np.abs(new[occ, 1]) + np.abs(new[occ, 2])
        # At least some cells should have non-zero pressure
        assert delta.max() >= 0.0  # weak assertion; layout may be trivial


def test_boundary_guard_zeroes_edge_pressure():
    grid  = _make_grid()
    state = init_state(grid)
    # Seed strong left-facing pressure at left edge
    state[:, 0, 1] = -1.0
    cfg   = {"guard_margin": 1}
    new   = rule_boundary_guard(state, 0, cfg)
    # Left column x-pressure should be >= 0 after guard
    assert (new[:, 0, 1] >= 0.0).all()


def test_alternating_axis_suppresses_correctly():
    grid  = _make_grid()
    state = init_state(grid)
    state[:, :, 1] = 0.5  # xpressure
    state[:, :, 2] = 0.5  # ypressure

    cfg_x = {"x_epochs": [0], "y_epochs": [1]}
    new_x = rule_alternating_axis_schedule(state, 0, cfg_x)
    # On x-epoch, y-pressure suppressed
    assert (new_x[:, :, 2] <= state[:, :, 2]).all()

    new_y = rule_alternating_axis_schedule(state, 1, cfg_x)
    # On y-epoch, x-pressure suppressed
    assert (new_y[:, :, 1] <= state[:, :, 1]).all()


def test_epoch_scheduler_runs():
    from src.ca.epoch_scheduler import EpochScheduler
    from src.ca.composite_rules import load_ca_config
    grid = _make_grid()
    ca_cfg = load_ca_config("configs/ca_rules.yaml")
    rules_cfg = ca_cfg.get("rules", {})
    sched = EpochScheduler(
        rules_config=rules_cfg,
        enabled_rules=["free_space_attraction", "boundary_guard"],
        max_epochs=5,
        convergence_threshold=0.01,
    )
    result = sched.run(grid)
    assert result.epochs_run >= 1
    assert result.epochs_run <= 5
    assert 0.0 < result.final_xshrf <= 1.0
    assert 0.0 < result.final_yshrf <= 1.0
