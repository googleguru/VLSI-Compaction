"""
Polygon utility functions for VLSI layout geometry.
All coordinates are in CIF integer units.
"""

import math
from typing import List, Tuple

Point  = Tuple[int, int]
Bbox   = Tuple[int, int, int, int]   # x0 y0 x1 y1
Poly   = List[Point]


def bbox_of(points: Poly) -> Bbox:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def bbox_area(bbox: Bbox) -> int:
    x0, y0, x1, y1 = bbox
    return max(0, x1 - x0) * max(0, y1 - y0)


def bbox_union(a: Bbox, b: Bbox) -> Bbox:
    return min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])


def bboxes_overlap(a: Bbox, b: Bbox) -> bool:
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def bbox_intersection_area(a: Bbox, b: Bbox) -> int:
    ix0 = max(a[0], b[0])
    iy0 = max(a[1], b[1])
    ix1 = min(a[2], b[2])
    iy1 = min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0
    return (ix1 - ix0) * (iy1 - iy0)


def polygon_area(points: Poly) -> float:
    """Shoelace formula. Positive for CCW ordering."""
    n = len(points)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return abs(area) / 2.0


def translate_bbox(bbox: Bbox, dx: int, dy: int) -> Bbox:
    x0, y0, x1, y1 = bbox
    return x0 + dx, y0 + dy, x1 + dx, y1 + dy


def expand_bbox(bbox: Bbox, margin: int) -> Bbox:
    x0, y0, x1, y1 = bbox
    return x0 - margin, y0 - margin, x1 + margin, y1 + margin


def centroid(points: Poly) -> Tuple[float, float]:
    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)
    return cx, cy


def manhattan_distance(a: Point, b: Point) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
