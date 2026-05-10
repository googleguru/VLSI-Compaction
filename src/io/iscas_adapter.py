"""
ISCAS benchmark adapter.

ISCAS-85/89 are gate-level netlists. A full synthesis + P&R flow must be run
externally to produce layout-ready CIF. This module handles:
  - discovery of pre-converted CIF under data/benchmarks/iscas/
  - skip logic with explicit reason reporting
  - normalization of any available CIF
"""

import os
import logging
from pathlib import Path
from .cif_reader import CIFReader
from .cif_writer import CIFWriter
from .geometry_normalizer import normalize_layout

logger = logging.getLogger(__name__)

_SKIP_REASON = (
    "ISCAS benchmarks require synthesis + place-and-route to produce CIF. "
    "Place converted CIF files under data/benchmarks/iscas/ to enable this benchmark."
)


def discover_iscas_files(iscas_dir: str):
    p = Path(iscas_dir)
    if not p.is_dir():
        logger.warning("ISCAS directory not found: %s  [%s]", iscas_dir, _SKIP_REASON)
        return []
    cif_files = sorted(p.glob("*.cif"))
    if not cif_files:
        logger.warning("No ISCAS CIF files in %s  [%s]", iscas_dir, _SKIP_REASON)
    return cif_files


def load_and_normalize_iscas(path: str):
    reader = CIFReader()
    layout = reader.read(path)
    return normalize_layout(layout)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--iscas-dir", default="data/benchmarks/iscas")
    parser.add_argument("--out-dir",   default="data/benchmarks/iscas_norm")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    files = discover_iscas_files(args.iscas_dir)
    if not files:
        print(f"[iscas_adapter] SKIP: {_SKIP_REASON}")
        return

    writer = CIFWriter()
    for f in files:
        try:
            layout = load_and_normalize_iscas(str(f))
            out = os.path.join(args.out_dir, f.name)
            writer.write(layout, out)
        except Exception as exc:
            logger.error("Failed %s: %s", f, exc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
