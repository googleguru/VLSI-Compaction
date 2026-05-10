"""
Region partitioner: splits layout bounding box into sub-regions for
spatial analysis and CA pressure-field seeding.
"""

import numpy as np
from typing import List, Tuple
from .polygon_utils import Bbox


def uniform_partition(bbox: Bbox, nx: int, ny: int) -> List[Bbox]:
    """Divide bbox into nx*ny uniform tiles."""
    x0, y0, x1, y1 = bbox
    xs = np.linspace(x0, x1, nx + 1)
    ys = np.linspace(y0, y1, ny + 1)
    tiles = []
    for i in range(nx):
        for j in range(ny):
            tiles.append((int(xs[i]), int(ys[j]), int(xs[i+1]), int(ys[j+1])))
    return tiles


def congestion_map(
    geometry_bboxes: List[Bbox], layout_bbox: Bbox, nx: int, ny: int
) -> np.ndarray:
    """
    Compute a normalized congestion density map.
    Returns an (ny, nx) float array in [0, 1].
    """
    tiles = uniform_partition(layout_bbox, nx, ny)
    density = np.zeros((ny, nx), dtype=float)
    total_area = max(1, sum(
        max(0, b[2] - b[0]) * max(0, b[3] - b[1]) for b in geometry_bboxes
    ))

    from .polygon_utils import bbox_intersection_area
    for idx, tile in enumerate(tiles):
        row, col = divmod(idx, nx)
        tile_area = max(1, (tile[2] - tile[0]) * (tile[3] - tile[1]))
        covered = sum(bbox_intersection_area(tile, g) for g in geometry_bboxes)
        density[row, col] = covered / tile_area

    return density
