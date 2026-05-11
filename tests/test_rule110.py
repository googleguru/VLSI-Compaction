"""
Tests for Rule-110 elementary cellular automaton core.

Validates:
- Exact Rule 110 truth table
- Boundary conditions (clamped and periodic)
- 2-D row/column pass application
- Full scheduler run: output shape, shrink factor range, pressure outputs
- Determinism across repeated runs
"""

import numpy as np
import pytest
from src.ca.rule110 import (
    apply_rule110_1d,
    apply_rule110_rows,
    apply_rule110_cols,
    row_activity,
    col_activity,
    fuse_pressure,
    _RULE110,
)
from src.ca.rule110_scheduler import Rule110Scheduler


# ── Truth table ──────────────────────────────────────────────────────────────

class TestRule110TruthTable:
    """Verify every neighbourhood entry in the truth table."""

    @pytest.mark.parametrize("L,C,R,expected", [
        (1, 1, 1, 0),
        (1, 1, 0, 1),
        (1, 0, 1, 1),
        (1, 0, 0, 0),
        (0, 1, 1, 1),
        (0, 1, 0, 1),
        (0, 0, 1, 1),
        (0, 0, 0, 0),
    ])
    def test_lookup(self, L, C, R, expected):
        idx = 4 * L + 2 * C + R
        assert int(_RULE110[idx]) == expected

    def test_rule_code_is_110(self):
        # Binary representation: index 0 to 7 → 0,1,1,0,1,1,1,0
        val = sum(int(_RULE110[i]) << i for i in range(8))
        assert val == 110


# ── 1-D updater ───────────────────────────────────────────────────────────────

class TestApplyRule110_1D:

    def test_all_zeros_stays_zero(self):
        row = np.zeros(10, dtype=np.float32)
        out = apply_rule110_1d(row)
        assert out.sum() == 0

    def test_all_ones_periodic(self):
        # All-1 row: every neighbourhood is (1,1,1) → 0
        row = np.ones(8, dtype=np.float32)
        out = apply_rule110_1d(row, boundary="periodic")
        assert out.sum() == 0

    def test_all_ones_clamped(self):
        # Interior cells: (1,1,1)→0.  Boundary cells differ.
        row = np.ones(8, dtype=np.float32)
        out = apply_rule110_1d(row, boundary="clamped")
        # Leftmost: (0,1,1)→1;  Rightmost: (1,1,0)→1; interior: (1,1,1)→0
        assert int(out[0]) == 1
        assert int(out[-1]) == 1
        assert out[1:-1].sum() == 0

    def test_single_cell_propagation(self):
        # Single 1 at position 4 in a row of 10
        row = np.zeros(10, dtype=np.float32)
        row[4] = 1.0
        out = apply_rule110_1d(row, boundary="clamped")
        # (0,0,1)→1, (0,1,0)→1, (1,0,0)→0
        assert int(out[3]) == 1  # (0,0,1) → 1
        assert int(out[4]) == 1  # (0,1,0) → 1
        assert int(out[5]) == 0  # (1,0,0) → 0

    def test_output_is_binary(self):
        rng = np.random.RandomState(0)
        row = rng.randint(0, 2, 20).astype(np.float32)
        out = apply_rule110_1d(row)
        assert set(out.tolist()).issubset({0, 1})

    def test_length_preserved(self):
        for n in [1, 5, 100]:
            row = np.zeros(n, dtype=np.float32)
            assert len(apply_rule110_1d(row)) == n


# ── 2-D passes ───────────────────────────────────────────────────────────────

class TestApplyRule110_2D:

    def test_row_pass_shape(self):
        grid = np.random.randint(0, 2, (8, 12)).astype(np.float32)
        out  = apply_rule110_rows(grid)
        assert out.shape == grid.shape

    def test_col_pass_shape(self):
        grid = np.random.randint(0, 2, (8, 12)).astype(np.float32)
        out  = apply_rule110_cols(grid)
        assert out.shape == grid.shape

    def test_row_pass_each_row_independent(self):
        # A single-row grid should give same result as 1-D updater
        row = np.array([[1, 0, 1, 1, 0, 0, 1, 0]], dtype=np.float32)
        out2d = apply_rule110_rows(row)
        out1d = apply_rule110_1d(row[0])
        np.testing.assert_array_equal(out2d[0], out1d)

    def test_row_and_col_binary(self):
        rng  = np.random.RandomState(42)
        grid = rng.randint(0, 2, (6, 10)).astype(np.float32)
        assert set(apply_rule110_rows(grid).flatten().tolist()).issubset({0, 1})
        assert set(apply_rule110_cols(grid).flatten().tolist()).issubset({0, 1})


# ── Activity and pressure ─────────────────────────────────────────────────────

class TestActivityPressure:

    def test_row_activity_all_ones(self):
        grid = np.ones((4, 6), dtype=np.float32)
        act  = row_activity(grid)
        assert act.shape == (4,)
        np.testing.assert_allclose(act, 1.0)

    def test_col_activity_all_zeros(self):
        grid = np.zeros((4, 6), dtype=np.float32)
        act  = col_activity(grid)
        assert act.shape == (6,)
        np.testing.assert_allclose(act, 0.0)

    def test_fuse_pressure_shape(self):
        row_act = np.array([0.2, 0.8, 0.5])
        col_act = np.array([0.1, 0.6, 0.3, 0.9])
        pmap    = fuse_pressure(row_act, col_act, (3, 4))
        assert pmap.shape == (3, 4)
        assert pmap.min() >= 0.0
        assert pmap.max() <= 1.0

    def test_fuse_pressure_range(self):
        rng     = np.random.RandomState(7)
        row_act = rng.rand(5).astype(np.float32)
        col_act = rng.rand(8).astype(np.float32)
        pmap    = fuse_pressure(row_act, col_act, (5, 8))
        assert float(pmap.min()) >= 0.0
        assert float(pmap.max()) <= 1.0


# ── Scheduler ────────────────────────────────────────────────────────────────

class TestRule110Scheduler:

    def _make_grid(self, seed=0, H=10, W=15, density=0.4):
        rng = np.random.RandomState(seed)
        return (rng.rand(H, W) < density).astype(np.float32)

    def test_epochs_run(self):
        sched  = Rule110Scheduler(max_epochs=10)
        grid   = self._make_grid()
        result = sched.run(grid)
        assert result.epochs_run == 10
        assert len(result.epoch_results) == 10

    def test_epoch_result_fields(self):
        sched  = Rule110Scheduler(max_epochs=5)
        grid   = self._make_grid()
        result = sched.run(grid)
        er = result.epoch_results[0]
        assert er.epoch == 0
        assert er.state.shape == grid.shape
        assert 0.0 <= er.active_fraction <= 1.0
        assert 0.0 <= er.suggested_xshrf <= 1.0
        assert 0.0 <= er.suggested_yshrf <= 1.0

    def test_alternating_pass_types(self):
        sched  = Rule110Scheduler(max_epochs=6, mode="alternating")
        grid   = self._make_grid()
        result = sched.run(grid)
        types  = [er.pass_type for er in result.epoch_results]
        assert types == ["row", "col", "row", "col", "row", "col"]

    def test_row_only_mode(self):
        sched  = Rule110Scheduler(max_epochs=4, mode="row_only")
        result = sched.run(self._make_grid())
        assert all(er.pass_type == "row" for er in result.epoch_results)

    def test_col_only_mode(self):
        sched  = Rule110Scheduler(max_epochs=4, mode="col_only")
        result = sched.run(self._make_grid())
        assert all(er.pass_type == "col" for er in result.epoch_results)

    def test_shrink_in_range(self):
        sched  = Rule110Scheduler(max_epochs=10, min_shrink=0.80, max_shrink=0.99)
        result = sched.run(self._make_grid(density=0.7))
        for er in result.epoch_results:
            assert 0.80 <= er.suggested_xshrf <= 0.99
            assert 0.80 <= er.suggested_yshrf <= 0.99

    def test_final_shrink_set(self):
        sched  = Rule110Scheduler(max_epochs=5)
        result = sched.run(self._make_grid())
        assert result.final_xshrf == result.epoch_results[-1].suggested_xshrf
        assert result.final_yshrf == result.epoch_results[-1].suggested_yshrf

    def test_pressure_history_length(self):
        sched  = Rule110Scheduler(max_epochs=8)
        result = sched.run(self._make_grid())
        xp, yp = result.pressure_history()
        assert len(xp) == 8
        assert len(yp) == 8

    def test_determinism(self):
        sched = Rule110Scheduler(max_epochs=10, seed=42)
        grid  = self._make_grid(seed=7)
        r1 = sched.run(grid.copy())
        r2 = sched.run(grid.copy())
        np.testing.assert_array_equal(
            r1.epoch_results[-1].state,
            r2.epoch_results[-1].state,
        )

    def test_all_zeros_grid(self):
        sched  = Rule110Scheduler(max_epochs=5)
        grid   = np.zeros((8, 8), dtype=np.float32)
        result = sched.run(grid)
        assert result.epochs_run == 5
        for er in result.epoch_results:
            assert er.active_fraction == 0.0

    def test_final_pressure_map_shape(self):
        H, W = 12, 16
        sched  = Rule110Scheduler(max_epochs=6)
        grid   = self._make_grid(H=H, W=W)
        result = sched.run(grid)
        assert result.final_pressure_map is not None
        assert result.final_pressure_map.shape == (H, W)

    def test_periodic_boundary(self):
        sched  = Rule110Scheduler(max_epochs=4, boundary="periodic")
        result = sched.run(self._make_grid())
        assert result.epochs_run == 4

    def test_damping_bounds(self):
        # With damping=1.0 the state is pure Rule 110 output (binary)
        sched  = Rule110Scheduler(max_epochs=3, damping=1.0)
        result = sched.run(self._make_grid())
        for er in result.epoch_results:
            unique_vals = set(np.unique(er.state).tolist())
            assert unique_vals.issubset({0.0, 1.0}), \
                f"With damping=1.0 state must be binary, got {unique_vals}"
