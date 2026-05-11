"""
Compaction planning layer.
Converts Rule-110 CA run results into backend compaction parameters.
"""
from .directional_pressure import (
    extract_dominant_direction,
    derive_iteration_schedule,
    weighted_shrink,
    pressure_map_from_result,
)
from .shrink_factor_planner import plan_shrink_factors
from .move_ordering import order_by_rule110_pressure

__all__ = [
    "extract_dominant_direction",
    "derive_iteration_schedule",
    "weighted_shrink",
    "pressure_map_from_result",
    "plan_shrink_factors",
    "order_by_rule110_pressure",
]
