"""
Grid discretizer: converts CIF layout geometry into a 2D occupancy grid
for the CA engine.
"""

import numpy as np
import logging
from typing import Tuple, List
from ..io.cif_reader import CIFLayout
from ..geometry.polygon_utils import Bbox

logger = logging.getLogger(__name__)


class GridDiscretizer:
    """
    Converts a CIFLayout into a 2D integer occupancy grid.

    Grid values:
      0 = EMPTY
      1 = OCCUPIED
      2 = KEEPOUT  (boundary / blocked)
      3 = BOUNDARY (layout outline)
    """

    EMPTY    = 0
    OCCUPIED = 1
    KEEPOUT  = 2
    BOUNDARY = 3

    def __init__(self, resolution: int = 10):
        self.resolution = resolution  # grid cells per layout unit

    def discretize(
        self, layout: CIFLayout, bbox: Bbox = None
    ) -> Tuple[np.ndarray, Bbox]:
        """
        Returns (grid, layout_bbox).
        grid shape: (rows, cols) = (height * resolution, width * resolution)
        """
        if bbox is None:
            bbox = layout.geometry_bbox()
        x0, y0, x1, y1 = bbox

        cols = max(1, (x1 - x0) * self.resolution // 100)
        rows = max(1, (y1 - y0) * self.resolution // 100)

        grid = np.zeros((rows, cols), dtype=np.int8)

        # Mark boundary
        grid[0, :]  = self.BOUNDARY
        grid[-1, :] = self.BOUNDARY
        grid[:, 0]  = self.BOUNDARY
        grid[:, -1] = self.BOUNDARY

        # Rasterize geometry
        all_bboxes = layout._collect_all_geometry()
        for gbbox in all_bboxes:
            self._fill_bbox(grid, gbbox, x0, y0, x1, y1, rows, cols, self.OCCUPIED)

        logger.debug(
            "Discretized layout to %dx%d grid, %d geometry shapes",
            rows, cols, len(all_bboxes),
        )
        return grid, bbox

    def _fill_bbox(
        self,
        grid: np.ndarray,
        gbbox: Bbox,
        lx0: int, ly0: int, lx1: int, ly1: int,
        rows: int, cols: int,
        value: int,
    ) -> None:
        bx0, by0, bx1, by1 = gbbox
        lw = max(1, lx1 - lx0)
        lh = max(1, ly1 - ly0)

        c0 = max(0, int((bx0 - lx0) * cols / lw))
        c1 = min(cols, int((bx1 - lx0) * cols / lw) + 1)
        r0 = max(0, int((by0 - ly0) * rows / lh))
        r1 = min(rows, int((by1 - ly0) * rows / lh) + 1)

        if c0 < c1 and r0 < r1:
            # Don't overwrite boundary
            mask = grid[r0:r1, c0:c1] != self.BOUNDARY
            grid[r0:r1, c0:c1][mask] = value
