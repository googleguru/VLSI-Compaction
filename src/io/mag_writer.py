"""
Magic VLSI .mag file writer.

Converts a CIFLayout to Magic's native ASCII format.
Each CIFSymbol becomes a separate .mag file (Magic's convention).
A top-level cell file is written that references all symbols via 'use' statements.

Magic .mag rect coordinates: (x_lower_left, y_lower_left, x_upper_right, y_upper_right)

Layer mapping: uses TechHandler.layer_map() to translate CIF layer names
to technology-appropriate Magic layer names (e.g. POLY → poly, METAL1 → metal1).
"""

import os
import time
import logging
from typing import Dict, Optional

from .cif_reader import CIFLayout, CIFSymbol, CIFBox
from ..layout.tech_handler import TechHandler

logger = logging.getLogger(__name__)

_TIMESTAMP = int(time.time())


class MagWriter:
    """
    Write a CIFLayout as a set of Magic .mag files.

    Parameters
    ----------
    tech : str
        Magic technology name for the header line.
    scale : int
        Divide CIF unit coordinates by this factor when writing .mag units.
        Inverse of MagReader.scale.  Default 1 (no scaling).
    top_name : str
        Name for the top-level cell file.
    """

    def __init__(
        self,
        tech: str = "scmos",
        scale: int = 1,
        top_name: str = "top",
    ):
        self.tech     = tech
        self.scale    = scale
        self.top_name = top_name
        self._lmap    = TechHandler(tech).layer_map()

    def write(self, layout: CIFLayout, out_dir: str) -> str:
        """
        Write layout to *out_dir*.  Returns path to the top-level .mag file.
        """
        os.makedirs(out_dir, exist_ok=True)
        sym_names: Dict[int, str] = {}

        # Write one .mag file per symbol
        for sym_num, sym in layout.symbols.items():
            cell_name = sym.name or f"cell_{sym_num}"
            cell_name = _safe_name(cell_name)
            sym_names[sym_num] = cell_name
            mag_path = os.path.join(out_dir, f"{cell_name}.mag")
            self._write_symbol(sym, cell_name, mag_path)

        # Write top-level cell that places all symbols
        top_path = os.path.join(out_dir, f"{self.top_name}.mag")
        self._write_top(layout, sym_names, top_path)
        logger.info("MagWriter: wrote %d cells + top to %s", len(sym_names), out_dir)
        return top_path

    def write_flat(self, layout: CIFLayout, out_path: str) -> str:
        """
        Write a single flat .mag file with all geometry at absolute positions
        (resolved through top_calls offsets).  Useful for DRC and rendering.
        """
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        layer_rects: Dict[str, list] = {}

        for call in (layout.top_calls or []):
            sym = layout.symbols.get(call.symbol_num)
            if sym is None:
                continue
            for box in sym.boxes:
                layer = self._lmap.resolve(box.layer)
                x1 = (box.cx - box.width  // 2 + call.tx) // self.scale
                y1 = (box.cy - box.height // 2 + call.ty) // self.scale
                x2 = (box.cx + box.width  // 2 + call.tx) // self.scale
                y2 = (box.cy + box.height // 2 + call.ty) // self.scale
                layer_rects.setdefault(layer, []).append((x1, y1, x2, y2))

        if not layer_rects and layout.symbols:
            # No top_calls: draw symbols at origin
            for sym in layout.symbols.values():
                for box in sym.boxes:
                    layer = self._lmap.resolve(box.layer)
                    x1 = (box.cx - box.width  // 2) // self.scale
                    y1 = (box.cy - box.height // 2) // self.scale
                    x2 = (box.cx + box.width  // 2) // self.scale
                    y2 = (box.cy + box.height // 2) // self.scale
                    layer_rects.setdefault(layer, []).append((x1, y1, x2, y2))

        cell_name = os.path.splitext(os.path.basename(out_path))[0]
        with open(out_path, "w") as fh:
            self._write_header(fh, cell_name)
            for layer, rects in sorted(layer_rects.items()):
                fh.write(f"<< {layer} >>\n")
                for x1, y1, x2, y2 in rects:
                    fh.write(f"rect {x1} {y1} {x2} {y2}\n")
            fh.write("<< end >>\n")

        logger.info("MagWriter: flat file → %s (%d layers)", out_path, len(layer_rects))
        return out_path

    # ── private ───────────────────────────────────────────────────────────────

    def _write_symbol(self, sym: CIFSymbol, cell_name: str, path: str) -> None:
        layer_rects: Dict[str, list] = {}
        for box in sym.boxes:
            layer = self._lmap.resolve(box.layer)
            x1 = (box.cx - box.width  // 2) // self.scale
            y1 = (box.cy - box.height // 2) // self.scale
            x2 = (box.cx + box.width  // 2) // self.scale
            y2 = (box.cy + box.height // 2) // self.scale
            layer_rects.setdefault(layer, []).append((x1, y1, x2, y2))

        for poly in sym.polygons:
            layer = self._lmap.resolve(poly.layer)
            if poly.points:
                xs = [p[0] // self.scale for p in poly.points]
                ys = [p[1] // self.scale for p in poly.points]
                # Approximate polygon as bounding-box rect in .mag
                layer_rects.setdefault(layer, []).append(
                    (min(xs), min(ys), max(xs), max(ys))
                )

        with open(path, "w") as fh:
            self._write_header(fh, cell_name)
            for layer, rects in sorted(layer_rects.items()):
                fh.write(f"<< {layer} >>\n")
                for x1, y1, x2, y2 in rects:
                    fh.write(f"rect {x1} {y1} {x2} {y2}\n")
            fh.write("<< end >>\n")

    def _write_top(
        self, layout: CIFLayout, sym_names: Dict[int, str], path: str
    ) -> None:
        cell_name = os.path.splitext(os.path.basename(path))[0]
        with open(path, "w") as fh:
            self._write_header(fh, cell_name)
            if layout.top_calls:
                fh.write("<< subcells >>\n")
                for call in layout.top_calls:
                    name = sym_names.get(call.symbol_num, f"cell_{call.symbol_num}")
                    tx = call.tx // self.scale
                    ty = call.ty // self.scale
                    fh.write(f"use {name} {name}_i{call.symbol_num}\n")
                    fh.write(f"array 1 1 1 1 {tx} {ty} 0 0\n")
                    fh.write(f"timestamp {_TIMESTAMP}\n")
            fh.write("<< end >>\n")

    def _write_header(self, fh, cell_name: str) -> None:
        fh.write("magic\n")
        fh.write(f"tech {self.tech}\n")
        fh.write(f"timestamp {_TIMESTAMP}\n")


def write_mag(layout: CIFLayout, out_dir: str, tech: str = "scmos",
              top_name: str = "top") -> str:
    """Module-level convenience: write hierarchical .mag files."""
    return MagWriter(tech=tech, top_name=top_name).write(layout, out_dir)


def write_mag_flat(layout: CIFLayout, out_path: str, tech: str = "scmos") -> str:
    """Module-level convenience: write a single flat .mag file."""
    return MagWriter(tech=tech).write_flat(layout, out_path)


def _safe_name(name: str) -> str:
    """Replace characters invalid in Magic cell names."""
    import re
    return re.sub(r"[^A-Za-z0-9_\-]", "_", name)[:64]
