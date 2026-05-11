"""
Magic VLSI .mag file reader.

Parses Magic's native ASCII layout format and converts it to a CIFLayout
so the rest of the pipeline can process .mag files transparently.

Magic .mag format (single-cell, flattened):
    magic
    tech <techname>
    timestamp <N>
    << <layer> >>
    rect x1 y1 x2 y2
    ...
    << labels >>
    rlabel <layer> x1 y1 x2 y2 <pos> <name>
    << subcells >>
    use <cellname> <instancename>
    array 1 1 1 1 <tx> <ty> 0 0
    timestamp <N>
    << end >>

Notes:
  - rect coordinates: (x_lower_left, y_lower_left, x_upper_right, y_upper_right)
  - Magic units vary by technology; stored as-is in CIF
  - Multi-cell designs: each cell is a separate .mag file; this reader handles
    the top-level cell and resolves 'use' references from the same directory
"""

import os
import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .cif_reader import CIFLayout, CIFSymbol, CIFBox, CIFCall

logger = logging.getLogger(__name__)

_LAYER_RE   = re.compile(r"^<<\s*(\S+.*?)\s*>>$")
_RECT_RE    = re.compile(r"^rect\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)")
_USE_RE     = re.compile(r"^use\s+(\S+)\s+(\S+)")
_ARRAY_RE   = re.compile(r"^array\s+\d+\s+\d+\s+\d+\s+\d+\s+(-?\d+)\s+(-?\d+)")
_TECH_RE    = re.compile(r"^tech\s+(\S+)")


@dataclass
class MagCell:
    name:   str
    tech:   str                        = "scmos"
    rects:  Dict[str, List[Tuple[int,int,int,int]]] = field(default_factory=dict)
    uses:   List[Tuple[str, int, int]] = field(default_factory=list)  # (cell, tx, ty)


class MagReader:
    """
    Parse a Magic .mag file and return a CIFLayout.

    Parameters
    ----------
    scale : int
        Multiply Magic unit coordinates by this factor when converting to CIF
        units.  For scmos (1 lambda = 100 CIF units), use scale=100.
        For sky130A (1 unit = 5 nm, CIF unit = 1 nm), use scale=1.
        Default 1 (no scaling; caller should rescale if needed).
    """

    def __init__(self, scale: int = 1):
        self.scale = scale

    def read(self, path: str) -> CIFLayout:
        """
        Read a .mag file and return a CIFLayout.
        Recursively resolves 'use' references found in the same directory.
        """
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Magic file not found: {path}")
        cell = self._parse_file(path)
        return self._to_cif(cell, os.path.dirname(path))

    # ── private ───────────────────────────────────────────────────────────────

    def _parse_file(self, path: str) -> MagCell:
        name = os.path.splitext(os.path.basename(path))[0]
        cell = MagCell(name=name)
        current_layer = ""
        pending_use   = ""
        tx = ty = 0

        with open(path) as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue

                m = _LAYER_RE.match(line)
                if m:
                    current_layer = m.group(1).lower()
                    continue

                m = _TECH_RE.match(line)
                if m:
                    cell.tech = m.group(1)
                    continue

                m = _RECT_RE.match(line)
                if m and current_layer not in ("end", "labels", "subcells"):
                    x1, y1, x2, y2 = (int(m.group(i)) for i in range(1, 5))
                    cell.rects.setdefault(current_layer, []).append(
                        (x1 * self.scale, y1 * self.scale,
                         x2 * self.scale, y2 * self.scale)
                    )
                    continue

                m = _USE_RE.match(line)
                if m:
                    pending_use = m.group(1)
                    tx = ty = 0
                    continue

                m = _ARRAY_RE.match(line)
                if m and pending_use:
                    tx = int(m.group(1)) * self.scale
                    ty = int(m.group(2)) * self.scale
                    cell.uses.append((pending_use, tx, ty))
                    pending_use = ""
                    continue

        logger.debug("MagReader: parsed %s (%d layers, %d subcells)",
                     name, len(cell.rects), len(cell.uses))
        return cell

    def _to_cif(self, cell: MagCell, search_dir: str) -> CIFLayout:
        layout    = CIFLayout()
        sym_num   = 1
        call_num  = 1
        cell_cache: Dict[str, int] = {}

        # One symbol per layer group (flat representation)
        for layer, rects in cell.rects.items():
            sym = CIFSymbol(number=sym_num, name=f"{cell.name}_{layer}")
            for x1, y1, x2, y2 in rects:
                w  = x2 - x1
                h  = y2 - y1
                cx = x1 + w // 2
                cy = y1 + h // 2
                sym.boxes.append(CIFBox(
                    layer  = layer.upper(),
                    width  = w,
                    height = h,
                    cx     = cx,
                    cy     = cy,
                ))
            layout.symbols[sym_num] = sym
            layout.top_calls.append(CIFCall(symbol_num=sym_num, tx=0, ty=0))
            cell_cache[layer] = sym_num
            sym_num += 1

        # Recursively handle subcell uses
        for (subcell_name, tx, ty) in cell.uses:
            sub_path = os.path.join(search_dir, f"{subcell_name}.mag")
            if not os.path.isfile(sub_path):
                logger.warning("MagReader: subcell file not found: %s", sub_path)
                continue
            sub_cell = self._parse_file(sub_path)
            # Inline subcell geometry at offset (tx, ty)
            for layer, rects in sub_cell.rects.items():
                sym = CIFSymbol(number=sym_num, name=f"{subcell_name}_{layer}")
                for x1, y1, x2, y2 in rects:
                    w  = x2 - x1
                    h  = y2 - y1
                    cx = x1 + w // 2
                    cy = y1 + h // 2
                    sym.boxes.append(CIFBox(
                        layer  = layer.upper(),
                        width  = w,
                        height = h,
                        cx     = cx,
                        cy     = cy,
                    ))
                layout.symbols[sym_num] = sym
                layout.top_calls.append(CIFCall(symbol_num=sym_num, tx=tx, ty=ty))
                sym_num += 1

        logger.info("MagReader: %s → %d symbols", cell.name, len(layout.symbols))
        return layout


def read_mag(path: str, scale: int = 1) -> CIFLayout:
    """Module-level convenience function."""
    return MagReader(scale=scale).read(path)
