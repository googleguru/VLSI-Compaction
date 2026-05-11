"""
Liberty file handler.

Reads a .lib Liberty file and extracts cell names and areas for use in
technology mapping and geometry template construction.  Does not implement
a full Liberty parser; uses regex to extract the subset needed for this flow.
"""

import os
import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CellInfo:
    name:    str
    area:    float          # liberty area attribute
    pg_pins: List[str] = field(default_factory=list)
    pins:    List[str] = field(default_factory=list)


class LibertyHandler:
    """
    Parse a Liberty .lib file and expose cell geometry hints.

    Parameters
    ----------
    path : str | None
        Path to the Liberty file.  If None or not present, available=False.
    """

    def __init__(self, path: Optional[str] = None):
        self.path = path
        self._cells: Dict[str, CellInfo] = {}
        self._parsed = False

        if path and os.path.isfile(path):
            self._parse()
        elif path:
            logger.warning("Liberty file not found: %s", path)

    @property
    def available(self) -> bool:
        return self.path is not None and os.path.isfile(self.path)

    @property
    def cells(self) -> Dict[str, CellInfo]:
        if not self._parsed and self.available:
            self._parse()
        return self._cells

    def cell_area(self, cell_name: str) -> Optional[float]:
        """Return the Liberty area for *cell_name*, or None if unknown."""
        info = self._cells.get(cell_name)
        return info.area if info else None

    def cell_names(self) -> List[str]:
        return list(self._cells.keys())

    # ── private ───────────────────────────────────────────────────────────────

    def _parse(self) -> None:
        try:
            with open(self.path) as fh:
                text = fh.read()
        except OSError as exc:
            logger.error("Cannot read liberty file: %s", exc)
            return

        # Extract cell blocks
        cell_pat = re.compile(
            r'cell\s*\(\s*"?(\w+)"?\s*\)\s*\{', re.MULTILINE
        )
        area_pat = re.compile(r'area\s*:\s*([\d.eE+\-]+)\s*;')
        pin_pat  = re.compile(r'pin\s*\(\s*"?(\w+)"?\s*\)')

        pos = 0
        for m in cell_pat.finditer(text):
            cell_name = m.group(1)
            start = m.end()
            block = self._extract_block(text, start)
            area_m = area_pat.search(block)
            area = float(area_m.group(1)) if area_m else 0.0
            pins = pin_pat.findall(block)
            self._cells[cell_name] = CellInfo(
                name=cell_name, area=area, pins=pins
            )

        self._parsed = True
        logger.info("Liberty: loaded %d cells from %s", len(self._cells), self.path)

    @staticmethod
    def _extract_block(text: str, start: int) -> str:
        """Extract balanced brace block starting just after the opening '{'."""
        depth = 1
        i = start
        while i < len(text) and depth > 0:
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
            i += 1
        return text[start:i]
