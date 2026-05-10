"""
Spatial metrics: area, bbox dimensions, reduction percentages.
"""

from typing import Optional, Tuple
from .polygon_utils import Bbox, bbox_area


def layout_area(bbox: Bbox) -> int:
    return bbox_area(bbox)


def layout_width(bbox: Bbox) -> int:
    return max(0, bbox[2] - bbox[0])


def layout_height(bbox: Bbox) -> int:
    return max(0, bbox[3] - bbox[1])


def area_reduction_pct(before: Bbox, after: Bbox) -> float:
    a_before = layout_area(before)
    a_after  = layout_area(after)
    if a_before == 0:
        return 0.0
    return 100.0 * (a_before - a_after) / a_before


def width_reduction_pct(before: Bbox, after: Bbox) -> float:
    w_before = layout_width(before)
    w_after  = layout_width(after)
    if w_before == 0:
        return 0.0
    return 100.0 * (w_before - w_after) / w_before


def height_reduction_pct(before: Bbox, after: Bbox) -> float:
    h_before = layout_height(before)
    h_after  = layout_height(after)
    if h_before == 0:
        return 0.0
    return 100.0 * (h_before - h_after) / h_before


def summarize_reduction(before: Bbox, after: Bbox) -> dict:
    return {
        "area_before":        layout_area(before),
        "area_after":         layout_area(after),
        "area_reduction_pct": area_reduction_pct(before, after),
        "width_before":       layout_width(before),
        "width_after":        layout_width(after),
        "width_reduction_pct":  width_reduction_pct(before, after),
        "height_before":      layout_height(before),
        "height_after":       layout_height(after),
        "height_reduction_pct": height_reduction_pct(before, after),
    }
