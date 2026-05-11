"""
Netlist-to-geometry mapper.

Converts a parsed gate-level netlist (from Yosys) into a CIF layout by:
1. Looking up bounding-box dimensions for each cell instance.
2. Placing cells in a row-based floorplan with configurable row height
   and inter-cell spacing.
3. Emitting a CIFLayout object that can be fed directly to the compaction
   backend via the existing CIF writer.

The mapper intentionally uses a simple row-based placement so the resulting
layout has realistic overlap patterns for the compaction benchmark to solve.
"""

import math
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from ..io.cif_reader import CIFLayout, CIFSymbol, CIFBox, CIFCall
from ..synth.netlist_parser import ParsedNetlist, CellInstance
from .cell_template_loader import CellTemplateLoader, CellTemplate

logger = logging.getLogger(__name__)

_SCALE = 100    # layout units per Liberty unit (1 lambda = 100 CIF units)


@dataclass
class PlacedCell:
    inst_name: str
    cell_type: str
    x0: int
    y0: int
    width: int
    height: int


class NetlistMapper:
    """
    Map a ParsedNetlist to a CIFLayout using bounding-box placement.

    Parameters
    ----------
    template_loader : CellTemplateLoader
    row_spacing : int
        Vertical gap between rows (CIF units).
    col_spacing : int
        Horizontal gap between cells within a row (CIF units).
    target_aspect : float
        Desired width/height ratio; drives how many cells per row.
    seed : int
        Deterministic seed (currently unused; placement is deterministic).
    """

    def __init__(
        self,
        template_loader: Optional[CellTemplateLoader] = None,
        row_spacing: int = 50,
        col_spacing: int = 30,
        target_aspect: float = 1.5,
        seed: int = 42,
    ):
        self.loader       = template_loader or CellTemplateLoader()
        self.row_spacing  = row_spacing
        self.col_spacing  = col_spacing
        self.target_aspect = target_aspect
        self.seed         = seed

    def map(self, netlist: ParsedNetlist) -> CIFLayout:
        """
        Convert *netlist* to a CIFLayout.
        Each cell instance becomes a box in a unique symbol.
        A single top-level symbol holds C (call) statements to place them.
        """
        instances = netlist.instances
        if not instances:
            logger.warning("Netlist has no instances; returning empty layout")
            return CIFLayout()

        # Load templates
        templates = {
            inst.inst_name: self.loader.get(inst.cell_type)
            for inst in instances
        }

        # Decide cells per row from target aspect ratio
        total_w = sum(t.width for t in templates.values())
        avg_h   = sum(t.height for t in templates.values()) / len(templates)
        if avg_h > 0:
            target_w = math.sqrt(total_w * avg_h * self.target_aspect)
        else:
            target_w = math.sqrt(total_w) * 2
        cells_per_row = max(1, round(target_w / (total_w / len(instances))))

        # Row-based placement
        placed: List[PlacedCell] = []
        x, y, row_height = 0, 0, 0
        col_in_row = 0

        for inst in instances:
            tmpl = templates[inst.inst_name]
            if col_in_row >= cells_per_row:
                y          += row_height + self.row_spacing
                x          = 0
                row_height = 0
                col_in_row = 0

            placed.append(PlacedCell(
                inst_name = inst.inst_name,
                cell_type = inst.cell_type,
                x0 = x, y0 = y,
                width  = tmpl.width,
                height = tmpl.height,
            ))
            x          += tmpl.width + self.col_spacing
            row_height  = max(row_height, tmpl.height)
            col_in_row += 1

        return self._build_cif(placed, netlist.top_module)

    # ── private ───────────────────────────────────────────────────────────────

    def _build_cif(self, placed: List[PlacedCell], top_name: str) -> CIFLayout:
        layout = CIFLayout()
        layout.top_calls = []

        # One symbol per cell instance (mirrors existing CIF conventions)
        for sym_num, pc in enumerate(placed, start=1):
            sym = CIFSymbol(number=sym_num, name=pc.inst_name)
            cx = pc.width  // 2
            cy = pc.height // 2
            sym.boxes.append(CIFBox(
                layer=pc.cell_type[:6].upper(),
                cx=cx, cy=cy,
                width=pc.width, height=pc.height,
                angle=0,
            ))
            layout.symbols[sym_num] = sym

            # Place via a top-level call with the absolute position offset
            layout.top_calls.append(CIFCall(
                symbol_num=sym_num,
                tx=pc.x0,
                ty=pc.y0,
            ))

        logger.info(
            "NetlistMapper: placed %d instances for top='%s'",
            len(placed), top_name,
        )
        return layout
