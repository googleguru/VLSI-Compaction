"""
Magic VLSI technology file handler.

Discovers installed Magic technology files and provides layer-name mapping
between CIF layer names and Magic/technology-specific layer names.

Supported technologies (open-source / freely available):
  scmos    — generic SCMOS (ships with Magic)
  sky130A  — SkyWater 130nm open PDK
  sky130B  — SkyWater 130nm alternate configuration
  gf180mcu — GlobalFoundries 180nm MCU
"""

import os
import shutil
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Known Magic technology search paths
_MAGIC_TECH_PATHS = [
    "/usr/share/magic/sys",
    "/usr/local/share/magic/sys",
    "/opt/magic/sys",
    "/usr/lib/magic/sys",
    os.path.expanduser("~/.magic"),
]

# Layer mapping: generic CIF name → technology-specific Magic name
# Each entry: cif_name → (scmos_name, sky130_name)
_LAYER_TABLE: List[Tuple[str, str, str]] = [
    # (generic_or_cif,    scmos,      sky130A)
    ("POLY",    "poly",     "poly"),
    ("NDIFF",   "ndiffusion","nsd"),
    ("PDIFF",   "pdiffusion","psd"),
    ("DIFF",    "ndiffusion","nsd"),
    ("NWELL",   "nwell",    "nwell"),
    ("PWELL",   "pwell",    "pwell"),
    ("CONT",    "contact",  "licon"),
    ("VIA1",    "via",      "mcon"),
    ("VIA2",    "via2",     "via"),
    ("VIA3",    "via3",     "via2"),
    ("METAL1",  "metal1",   "li"),
    ("METAL2",  "metal2",   "met1"),
    ("METAL3",  "metal3",   "met2"),
    ("METAL4",  "metal4",   "met3"),
    ("METAL5",  "metal5",   "met4"),
    ("M1",      "metal1",   "li"),
    ("M2",      "metal2",   "met1"),
    ("M3",      "metal3",   "met2"),
    # Yosys internal cell layer names
    ("NAND2_X", "poly",     "poly"),
    ("INV_X",   "poly",     "poly"),
    ("DFF_X",   "metal1",   "li"),
]


@dataclass
class LayerMap:
    tech: str
    mapping: Dict[str, str] = field(default_factory=dict)

    def resolve(self, cif_layer: str) -> str:
        """Return the Magic layer name for a CIF layer; fall back to lowercase."""
        upper = cif_layer.upper()
        if upper in self.mapping:
            return self.mapping[upper]
        # Try prefix match (e.g. "NAND2_X1" → "poly")
        for key, val in self.mapping.items():
            if upper.startswith(key):
                return val
        return cif_layer.lower()


class TechHandler:
    """
    Locate Magic technology files and build layer mappings.

    Parameters
    ----------
    tech : str
        Technology name: 'scmos' (default), 'sky130A', 'sky130B', 'gf180mcu'
    """

    def __init__(self, tech: str = "scmos"):
        self.tech = tech
        self._tech_file: Optional[str] = None
        self._discover()

    @property
    def tech_file(self) -> Optional[str]:
        return self._tech_file

    @property
    def available(self) -> bool:
        return self._tech_file is not None

    def layer_map(self) -> LayerMap:
        """Return CIF→Magic layer name mapping for this technology."""
        col = 1 if self.tech == "scmos" else 2   # column index in _LAYER_TABLE
        mapping: Dict[str, str] = {}
        for row in _LAYER_TABLE:
            mapping[row[0].upper()] = row[col]
        return LayerMap(tech=self.tech, mapping=mapping)

    def magic_layer_names(self) -> List[str]:
        """Return the set of unique Magic layer names for this technology."""
        lmap = self.layer_map()
        return sorted(set(lmap.mapping.values()))

    # ── private ───────────────────────────────────────────────────────────────

    def _discover(self) -> None:
        for base in _MAGIC_TECH_PATHS:
            candidate = os.path.join(base, f"{self.tech}.tech")
            if os.path.isfile(candidate):
                self._tech_file = candidate
                logger.info("Magic tech file: %s", candidate)
                return

        # Magic may also accept bare tech names without a path
        if shutil.which("magic"):
            self._tech_file = self.tech   # magic will search its own path
            logger.info("Magic available; using built-in tech: %s", self.tech)
        else:
            logger.info(
                "Magic tech file '%s.tech' not found and magic not on PATH.",
                self.tech,
            )
