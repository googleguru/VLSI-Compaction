"""
Cellular automaton layer.

Primary CA: Rule 110 (rule110.py + rule110_scheduler.py)
Legacy CA:  7-rule composite (composite_rules.py + epoch_scheduler.py)
"""
from .rule110 import (
    apply_rule110_1d,
    apply_rule110_rows,
    apply_rule110_cols,
    row_activity,
    col_activity,
    fuse_pressure,
)
from .rule110_scheduler import Rule110Scheduler, Rule110RunResult, Rule110EpochResult

__all__ = [
    "apply_rule110_1d",
    "apply_rule110_rows",
    "apply_rule110_cols",
    "row_activity",
    "col_activity",
    "fuse_pressure",
    "Rule110Scheduler",
    "Rule110RunResult",
    "Rule110EpochResult",
]
