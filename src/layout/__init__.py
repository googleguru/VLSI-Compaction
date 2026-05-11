"""
Magic VLSI layout integration.

MagicRunner  — batch-mode interface to Magic (format conversion, DRC, rendering)
TechHandler  — technology file discovery and layer-name mapping
"""
from .magic_runner import MagicRunner, MagicDRCResult, MagicBBoxResult
from .tech_handler import TechHandler, LayerMap

__all__ = [
    "MagicRunner", "MagicDRCResult", "MagicBBoxResult",
    "TechHandler", "LayerMap",
]
