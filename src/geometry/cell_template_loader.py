"""
Cell geometry template loader.

Loads bounding-box dimensions for standard cells from a YAML template file.
When real layout views are absent (no PDK), synthetic fallback dimensions
are generated from the cell name heuristic and Liberty area if available.

Template YAML format
--------------------
cells:
  INV_X1:  {width: 200, height: 400, layers: [M1, DIFF]}
  NAND2_X1: {width: 280, height: 400}
  ...
defaults:
  height: 400
  width_per_pin: 80
  min_width: 160
"""

import os
import re
import logging
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_FALLBACK_TEMPLATES_PATH = os.path.join(
    os.path.dirname(__file__), "../../data/synth/cell_templates.yaml"
)


@dataclass
class CellTemplate:
    name:   str
    width:  int        # in CIF units (centimicrons)
    height: int
    layers: List[str] = field(default_factory=lambda: ["POLY"])


class CellTemplateLoader:
    """
    Load cell geometry templates from a YAML file.

    Parameters
    ----------
    template_path : str | None
        Path to cell_templates.yaml.  Falls back to the bundled file at
        data/synth/cell_templates.yaml.
    """

    def __init__(self, template_path: Optional[str] = None):
        self._path = template_path or _FALLBACK_TEMPLATES_PATH
        self._cells: Dict[str, CellTemplate] = {}
        self._defaults: dict = {}
        self._loaded = False
        self._load()

    def get(self, cell_name: str) -> CellTemplate:
        """
        Return the template for *cell_name*.
        Falls back to a synthetic estimate if not in the table.
        """
        if cell_name in self._cells:
            return self._cells[cell_name]
        return self._synthetic(cell_name)

    def known_cells(self) -> List[str]:
        return list(self._cells.keys())

    # ── private ───────────────────────────────────────────────────────────────

    def _load(self) -> None:
        path = os.path.normpath(self._path)
        if not os.path.isfile(path):
            logger.warning(
                "Cell template file not found: %s — using synthetic fallback",
                path,
            )
            return
        try:
            with open(path) as fh:
                data = yaml.safe_load(fh)
        except Exception as exc:
            logger.error("Cannot load cell templates: %s", exc)
            return

        self._defaults = data.get("defaults", {})
        for name, info in (data.get("cells") or {}).items():
            w = int(info.get("width",  self._defaults.get("min_width", 160)))
            h = int(info.get("height", self._defaults.get("height",    400)))
            layers = info.get("layers", ["POLY"])
            self._cells[name] = CellTemplate(name=name, width=w, height=h, layers=layers)

        self._loaded = True
        logger.info("Cell templates: loaded %d entries from %s", len(self._cells), path)

    def _synthetic(self, cell_name: str) -> CellTemplate:
        """Estimate cell dimensions from cell name patterns."""
        h = int(self._defaults.get("height", 400))
        w_per_pin = int(self._defaults.get("width_per_pin", 80))
        min_w     = int(self._defaults.get("min_width",     160))

        # Infer input count from name: NAND2 → 2, AOI21 → 3, etc.
        m = re.search(r'(\d+)$', cell_name.upper().split('_')[0])
        pin_count = int(m.group(1)) if m else 2
        # Multi-input cells: AOI21, OAI211 etc.
        digit_sum = sum(int(d) for d in re.findall(r'\d', cell_name[:6]))
        pin_count = max(pin_count, digit_sum, 2)

        w = max(min_w, w_per_pin * pin_count)
        logger.debug("Synthetic template for %s: %dx%d", cell_name, w, h)
        return CellTemplate(name=cell_name, width=w, height=h)
