"""
Overlap and spacing violation estimators for VLSI layout validation.
Uses axis-aligned bounding boxes as a proxy when full polygon DRC is unavailable.
"""

import logging
from typing import List, Tuple, Dict
from .polygon_utils import Bbox, bboxes_overlap, bbox_intersection_area

logger = logging.getLogger(__name__)


def count_bbox_overlaps(bboxes: List[Bbox]) -> int:
    """O(n^2) overlap counter. Acceptable for small layouts."""
    count = 0
    for i in range(len(bboxes)):
        for j in range(i + 1, len(bboxes)):
            if bboxes_overlap(bboxes[i], bboxes[j]):
                count += 1
    return count


def total_overlap_area(bboxes: List[Bbox]) -> int:
    total = 0
    for i in range(len(bboxes)):
        for j in range(i + 1, len(bboxes)):
            total += bbox_intersection_area(bboxes[i], bboxes[j])
    return total


def min_spacing(bboxes: List[Bbox]) -> float:
    """Minimum edge-to-edge spacing across all non-overlapping bbox pairs."""
    import math
    min_sp = math.inf
    for i in range(len(bboxes)):
        for j in range(i + 1, len(bboxes)):
            sp = _edge_spacing(bboxes[i], bboxes[j])
            if sp >= 0 and sp < min_sp:
                min_sp = sp
    return min_sp if min_sp != math.inf else 0.0


def _edge_spacing(a: Bbox, b: Bbox) -> float:
    """Signed edge-to-edge gap. Negative means overlap."""
    gap_x = max(a[0], b[0]) - min(a[2], b[2])
    gap_y = max(a[1], b[1]) - min(a[3], b[3])
    # Only one axis has a gap for non-overlapping boxes
    if gap_x > 0 and gap_y <= 0:
        return float(gap_x)
    if gap_y > 0 and gap_x <= 0:
        return float(gap_y)
    if gap_x > 0 and gap_y > 0:
        return float((gap_x**2 + gap_y**2) ** 0.5)
    return float(min(gap_x, gap_y))  # negative = overlap


def spacing_violations(bboxes: List[Bbox], min_space: int) -> int:
    """Count pairs with edge-to-edge spacing below min_space (DRC proxy)."""
    violations = 0
    for i in range(len(bboxes)):
        for j in range(i + 1, len(bboxes)):
            sp = _edge_spacing(bboxes[i], bboxes[j])
            if 0 <= sp < min_space:
                violations += 1
    return violations
