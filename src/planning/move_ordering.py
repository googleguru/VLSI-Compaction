"""
Rule-110 guided move ordering for pre-compaction cell sequencing.

Cells in high-pressure regions (as determined by the Rule-110 pressure map)
are prioritised for compaction.  This biases the segment-tree backend to
process the most constrained regions first, improving runtime efficiency.
"""

import numpy as np
import logging
from typing import Dict, List, Tuple

from ..io.cif_reader import CIFLayout
from .directional_pressure import pressure_map_from_result

logger = logging.getLogger(__name__)


def order_by_rule110_pressure(
    layout: CIFLayout,
    run_result,
    discretizer,
) -> List[int]:
    """
    Return symbol numbers ordered by descending Rule-110 pressure score.

    Parameters
    ----------
    layout : CIFLayout
    run_result : Rule110RunResult or CARunResult
    discretizer : GridDiscretizer (used to map layout coords to grid cells)
    """
    pmap = pressure_map_from_result(run_result)
    if pmap.size <= 1:
        # No 2-D map available; fall back to area ordering
        return _order_by_area(layout)

    scores: List[Tuple[int, float]] = []
    for sym_num, sym in layout.symbols.items():
        bboxes = _symbol_bboxes(sym)
        if not bboxes:
            scores.append((sym_num, 0.0))
            continue
        score = _region_pressure(pmap, bboxes, discretizer)
        scores.append((sym_num, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in scores]


def _region_pressure(pmap, bboxes, discretizer) -> float:
    """Sample the pressure map at grid cells covered by bboxes."""
    H, W = pmap.shape
    res  = getattr(discretizer, "resolution", 10)
    total = 0.0
    count = 0
    for x0, y0, x1, y1 in bboxes:
        r0, c0 = int(y0 / res), int(x0 / res)
        r1, c1 = int(y1 / res), int(x1 / res)
        r0, c0 = max(0, r0), max(0, c0)
        r1, c1 = min(H - 1, r1), min(W - 1, c1)
        if r1 >= r0 and c1 >= c0:
            total += float(pmap[r0:r1+1, c0:c1+1].sum())
            count += (r1 - r0 + 1) * (c1 - c0 + 1)
    return total / max(count, 1)


def _symbol_bboxes(sym) -> List[Tuple[int, int, int, int]]:
    bboxes = []
    for b in sym.boxes:
        hw, hh = b.width // 2, b.height // 2
        bboxes.append((b.cx - hw, b.cy - hh, b.cx + hw, b.cy + hh))
    for p in sym.polygons:
        xs = [pt[0] for pt in p.points]
        ys = [pt[1] for pt in p.points]
        bboxes.append((min(xs), min(ys), max(xs), max(ys)))
    return bboxes


def _order_by_area(layout: CIFLayout) -> List[int]:
    areas = []
    for num, sym in layout.symbols.items():
        a = sum(b.width * b.height for b in sym.boxes)
        areas.append((num, a))
    areas.sort(key=lambda x: x[1], reverse=True)
    return [n for n, _ in areas]
