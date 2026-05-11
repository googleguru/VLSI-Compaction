"""
Helper that optionally runs Magic DRC on a CIF or .mag layout file.

Falls back to the simple geometry overlap estimator when Magic is absent.
All callers pass a CIF path; Magic is invoked in batch mode if available.
"""

import logging
import os
from typing import Tuple

from ..layout.magic_runner import MagicRunner
from ..geometry.overlap_estimator import count_bbox_overlaps, spacing_violations

logger = logging.getLogger(__name__)

_DEFAULT_TECH = "scmos"


def drc_violations(
    cif_path: str,
    bboxes: list,
    spacing_lambda: int = 1,
    magic_runner: "MagicRunner | None" = None,
    magic_tech: str = _DEFAULT_TECH,
) -> Tuple[int, bool]:
    """
    Return (violation_count, magic_was_used).

    If Magic is available and *cif_path* exists, run Magic DRC and return its
    count.  Otherwise fall back to the simple bounding-box overlap estimator.

    Parameters
    ----------
    cif_path : str
        Path to the CIF file to check.
    bboxes : list
        Pre-computed bounding boxes (used as fallback only).
    spacing_lambda : int
        Minimum spacing in lambda units (for fallback estimator).
    magic_runner : MagicRunner | None
        Re-use an existing runner; a new one is created if None.
    magic_tech : str
        Technology for Magic DRC (default 'scmos').
    """
    if magic_runner is None:
        magic_runner = MagicRunner(tech=magic_tech)

    if magic_runner.available and os.path.isfile(cif_path):
        result = magic_runner.run_drc_on_cif(cif_path)
        if result.success:
            logger.debug(
                "Magic DRC on %s: %d violations", cif_path, result.violations
            )
            return result.violations, True
        logger.debug("Magic DRC failed (%s); using overlap estimator", result.error)

    # Fallback: geometry overlap estimator
    n = (count_bbox_overlaps(bboxes)
         + spacing_violations(bboxes, spacing_lambda))
    return n, False
