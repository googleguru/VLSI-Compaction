"""
Tests for geometry utilities: polygon ops, overlap estimation, spatial metrics.
"""

import pytest
from src.geometry.polygon_utils import (
    bbox_of, bbox_area, bbox_union, bboxes_overlap,
    bbox_intersection_area, polygon_area, translate_bbox, expand_bbox,
)
from src.geometry.overlap_estimator import (
    count_bbox_overlaps, total_overlap_area, min_spacing
)
from src.geometry.spatial_metrics import (
    area_reduction_pct, width_reduction_pct, height_reduction_pct,
    summarize_reduction,
)
from src.io.geometry_normalizer import normalize_layout
from src.io.cif_reader import CIFReader
import textwrap


def test_bbox_of():
    pts = [(0, 0), (10, 0), (10, 5), (0, 5)]
    assert bbox_of(pts) == (0, 0, 10, 5)


def test_bbox_area():
    assert bbox_area((0, 0, 10, 5)) == 50
    assert bbox_area((0, 0, 0, 0)) == 0


def test_bbox_union():
    a = (0, 0, 5, 5)
    b = (3, 3, 8, 8)
    assert bbox_union(a, b) == (0, 0, 8, 8)


def test_bboxes_overlap_true():
    assert bboxes_overlap((0, 0, 5, 5), (3, 3, 8, 8))


def test_bboxes_overlap_false():
    assert not bboxes_overlap((0, 0, 4, 4), (5, 5, 9, 9))


def test_bbox_intersection_area():
    assert bbox_intersection_area((0, 0, 5, 5), (3, 3, 8, 8)) == 4
    assert bbox_intersection_area((0, 0, 4, 4), (5, 5, 9, 9)) == 0


def test_polygon_area_square():
    pts = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert polygon_area(pts) == 100.0


def test_polygon_area_triangle():
    pts = [(0, 0), (6, 0), (0, 4)]
    assert polygon_area(pts) == 12.0


def test_translate_bbox():
    assert translate_bbox((1, 2, 5, 6), 3, -1) == (4, 1, 8, 5)


def test_expand_bbox():
    assert expand_bbox((2, 2, 8, 8), 1) == (1, 1, 9, 9)


def test_count_bbox_overlaps_none():
    boxes = [(0, 0, 4, 4), (5, 0, 9, 4), (10, 0, 14, 4)]
    assert count_bbox_overlaps(boxes) == 0


def test_count_bbox_overlaps_one():
    boxes = [(0, 0, 5, 5), (3, 3, 8, 8)]
    assert count_bbox_overlaps(boxes) == 1


def test_total_overlap_area():
    boxes = [(0, 0, 5, 5), (3, 3, 8, 8)]
    assert total_overlap_area(boxes) == 4


def test_area_reduction_pct():
    before = (0, 0, 10, 10)
    after  = (0, 0, 8, 8)
    assert abs(area_reduction_pct(before, after) - 36.0) < 0.01


def test_summarize_reduction():
    before = (0, 0, 100, 80)
    after  = (0, 0, 80, 60)
    r = summarize_reduction(before, after)
    assert r["width_before"] == 100
    assert r["width_after"]  == 80
    assert abs(r["width_reduction_pct"] - 20.0) < 0.01
    assert r["height_before"] == 80
    assert abs(r["height_reduction_pct"] - 25.0) < 0.01


def test_normalize_layout_origin():
    cif = textwrap.dedent("""\
        DS 1 1 2;
        L POLY;
        B 100 100 550 350;
        DF;
        C 1;
        E
    """)
    reader = CIFReader()
    layout = reader.read_string(cif)
    layout = normalize_layout(layout)
    x0, y0, _, _ = layout.geometry_bbox()
    assert x0 == 0
    assert y0 == 0
