"""
IPSD benchmark adapter.

IPSD layout-ready CIF files are not publicly auto-downloadable.
This module provides:
  - file discovery under data/benchmarks/ipsd/
  - basic geometry normalization
  - skip logging when files are absent
"""

import os
import logging
import argparse
from pathlib import Path
from .cif_reader import CIFReader
from .cif_writer import CIFWriter
from .geometry_normalizer import normalize_layout

logger = logging.getLogger(__name__)


def discover_ipsd_files(ipsd_dir: str):
    p = Path(ipsd_dir)
    if not p.is_dir():
        logger.warning("IPSD directory not found: %s", ipsd_dir)
        return []
    cif_files = sorted(p.glob("*.cif"))
    if not cif_files:
        logger.warning(
            "No CIF files in %s. Provide layout-ready IPSD CIF files to enable "
            "IPSD benchmarks.", ipsd_dir
        )
    return cif_files


def load_and_normalize_ipsd(path: str):
    reader = CIFReader()
    layout = reader.read(path)
    layout = normalize_layout(layout)
    return layout


def main():
    parser = argparse.ArgumentParser(description="IPSD benchmark adapter")
    parser.add_argument("--ipsd-dir", default="data/benchmarks/ipsd")
    parser.add_argument("--out-dir", default="data/benchmarks/ipsd_norm")
    parser.add_argument("--mode", choices=["normalize", "asap7"], default="normalize")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    files = discover_ipsd_files(args.ipsd_dir)
    if not files:
        print(f"[ipsd_adapter] SKIP: no CIF files found in {args.ipsd_dir}")
        return

    writer = CIFWriter()
    for f in files:
        try:
            layout = load_and_normalize_ipsd(str(f))
            out_path = os.path.join(args.out_dir, f.name)
            writer.write(layout, out_path)
            logger.info("Normalized %s -> %s", f, out_path)
        except Exception as exc:
            logger.error("Failed to process %s: %s", f, exc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
