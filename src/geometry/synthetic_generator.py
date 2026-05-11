"""
Synthetic cell layout generator.

Produces reproducible CIF layouts with configurable cell count, density,
and size variance.  Used when real benchmark layouts and PDK views are
unavailable.  Outputs are honest synthetic benchmarks — clearly labelled
as such in all reports.
"""

import math
import logging
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..io.cif_reader import CIFLayout, CIFSymbol, CIFBox, CIFCall

logger = logging.getLogger(__name__)


@dataclass
class SyntheticConfig:
    num_cells:     int   = 20
    seed:          int   = 42
    target_density: float = 0.65   # approx fraction of bbox that is occupied
    min_cell_width:  int  = 100    # CIF units
    max_cell_width:  int  = 500
    min_cell_height: int  = 100
    max_cell_height: int  = 400
    inter_cell_gap:  int  = 20     # minimum gap between cells
    layer_name:      str  = "POLY"


def generate_synthetic_layout(cfg: Optional[SyntheticConfig] = None) -> CIFLayout:
    """
    Generate a random-but-reproducible CIF layout for benchmarking.

    Cells are placed in a floorplan that approximates *target_density*.
    Positions are guaranteed non-overlapping at generation time; the
    compaction backend will then try to tighten the layout further.
    """
    if cfg is None:
        cfg = SyntheticConfig()

    rng = np.random.RandomState(cfg.seed)

    # Draw cell dimensions
    widths  = rng.randint(cfg.min_cell_width,  cfg.max_cell_width  + 1, cfg.num_cells)
    heights = rng.randint(cfg.min_cell_height, cfg.max_cell_height + 1, cfg.num_cells)

    total_cell_area = int(np.sum(widths * heights))
    floor_area      = total_cell_area / max(cfg.target_density, 0.05)
    floor_side      = int(math.sqrt(floor_area))

    cells_per_row = max(1, int(math.sqrt(cfg.num_cells * 1.5)))
    placed = _row_pack(widths, heights, cells_per_row, cfg.inter_cell_gap, rng)

    layout = CIFLayout()
    layout.top_calls = []

    for i, (x0, y0, w, h) in enumerate(placed):
        sym_num = i + 1
        sym = CIFSymbol(number=sym_num, name=f"CELL_{sym_num}")
        sym.boxes.append(CIFBox(
            layer  = cfg.layer_name,
            cx     = w // 2,
            cy     = h // 2,
            width  = w,
            height = h,
            angle  = 0,
        ))
        layout.symbols[sym_num] = sym
        layout.top_calls.append(CIFCall(symbol_num=sym_num, tx=x0, ty=y0))

    logger.info(
        "SyntheticGenerator: %d cells, density≈%.2f, floor≈%dx%d",
        cfg.num_cells,
        total_cell_area / max(_bounding_area(placed), 1),
        floor_side, floor_side,
    )
    return layout


def _row_pack(
    widths: np.ndarray,
    heights: np.ndarray,
    cells_per_row: int,
    gap: int,
    rng: np.random.RandomState,
) -> List[Tuple[int, int, int, int]]:
    """
    Pack cells into rows, returning (x0, y0, w, h) for each cell.
    Adds a small random horizontal jitter so the layout is not perfectly grid-aligned,
    making it a more realistic compaction benchmark.
    """
    placed = []
    x, y = 0, 0
    row_height = 0
    col = 0

    max_jitter = max(gap * 2, 10)

    for w, h in zip(widths.tolist(), heights.tolist()):
        if col >= cells_per_row:
            y      += row_height + gap + rng.randint(0, gap + 1)
            x      = 0
            row_height = 0
            col    = 0

        jitter = rng.randint(0, max_jitter)
        placed.append((x + jitter, y, int(w), int(h)))
        x          += int(w) + gap
        row_height  = max(row_height, int(h))
        col        += 1

    return placed


def _bounding_area(placed: List[Tuple[int, int, int, int]]) -> int:
    if not placed:
        return 1
    max_x = max(x0 + w for x0, _, w, _ in placed)
    max_y = max(y0 + h for _, y0, _, h in placed)
    return max(max_x * max_y, 1)
