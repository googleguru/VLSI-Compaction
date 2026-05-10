"""
Pre-compaction cell ordering strategies.
Orders cells / symbols for compaction to maximize CA pressure utilization.
"""

import logging
from typing import List, Tuple, Dict
from ..io.cif_reader import CIFLayout, CIFSymbol
from ..geometry.polygon_utils import bbox_area, Bbox

logger = logging.getLogger(__name__)


def order_by_area_descending(layout: CIFLayout) -> List[int]:
    """Return symbol numbers sorted by total geometry area, largest first."""
    sym_areas: List[Tuple[int, int]] = []
    for num, sym in layout.symbols.items():
        area = _symbol_area(layout, sym)
        sym_areas.append((num, area))
    sym_areas.sort(key=lambda x: x[1], reverse=True)
    return [num for num, _ in sym_areas]


def order_by_x_coordinate(layout: CIFLayout) -> List[int]:
    """Order symbols by their leftmost x coordinate (left-to-right)."""
    sym_positions: List[Tuple[int, int]] = []
    for num, sym in layout.symbols.items():
        x0 = _symbol_min_x(layout, sym)
        sym_positions.append((num, x0))
    sym_positions.sort(key=lambda x: x[1])
    return [num for num, _ in sym_positions]


def order_by_pressure_magnitude(
    layout: CIFLayout, pressure_map: Dict[int, Tuple[float, float]]
) -> List[int]:
    """
    Order symbols by |xp| + |yp| pressure magnitude (highest first).
    pressure_map maps symbol_num -> (xp, yp).
    """
    scored: List[Tuple[int, float]] = []
    for num in layout.symbols:
        xp, yp = pressure_map.get(num, (0.0, 0.0))
        score = abs(xp) + abs(yp)
        scored.append((num, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [num for num, _ in scored]


def _symbol_area(layout: CIFLayout, sym: CIFSymbol) -> int:
    total = 0
    for b in sym.boxes:
        total += b.width * b.height
    for p in sym.polygons:
        from ..geometry.polygon_utils import polygon_area
        total += int(polygon_area(p.points))
    return total


def _symbol_min_x(layout: CIFLayout, sym: CIFSymbol) -> int:
    xs = []
    for b in sym.boxes:
        xs.append(b.cx - b.width // 2)
    for p in sym.polygons:
        xs.extend(pt[0] for pt in p.points)
    return min(xs) if xs else 0
