"""
Geometry normalizer: translates layouts to origin (0,0), validates CIF geometry,
and writes normalized files ready for the compaction backend.
"""

import os
import logging
import argparse
from .cif_reader import CIFLayout, CIFReader, CIFBox, CIFPolygon, CIFWire
from .cif_writer import CIFWriter

logger = logging.getLogger(__name__)


def normalize_layout(layout: CIFLayout) -> CIFLayout:
    """Translate layout so its bounding box starts at (0,0)."""
    x0, y0, _, _ = layout.geometry_bbox()
    if x0 == 0 and y0 == 0:
        return layout
    _translate_layout(layout, -x0, -y0)
    return layout


def _translate_layout(layout: CIFLayout, dx: int, dy: int) -> None:
    if layout.top_calls:
        # Shift top-level call origins only; symbol geometry is relative to each call.
        # _symbol_bboxes already applies (call.tx, call.ty) as an additive offset,
        # so translating symbol internals AND call offsets would double-count.
        for call in layout.top_calls:
            call.tx += dx
            call.ty += dy
    else:
        # No top-level calls: symbol geometry is absolute, translate it directly.
        for sym in layout.symbols.values():
            _translate_symbol(sym, dx, dy)


def _translate_symbol(sym, dx: int, dy: int) -> None:
    for b in sym.boxes:
        b.cx += dx
        b.cy += dy
    for p in sym.polygons:
        p.points = [(x + dx, y + dy) for x, y in p.points]
    for w in sym.wires:
        w.points = [(x + dx, y + dy) for x, y in w.points]
    for c in sym.calls:
        c.tx += dx
        c.ty += dy


def validate_layout(layout: CIFLayout) -> list:
    """Return list of warning strings for suspicious geometry."""
    warnings = []
    for sym in layout.symbols.values():
        for b in sym.boxes:
            if b.width <= 0 or b.height <= 0:
                warnings.append(f"Symbol {sym.number}: degenerate box {b}")
        for p in sym.polygons:
            if len(p.points) < 3:
                warnings.append(f"Symbol {sym.number}: polygon with < 3 points")
    return warnings


def main():
    parser = argparse.ArgumentParser(description="Normalize CIF geometry files")
    parser.add_argument("--ipsd-dir",  default="data/benchmarks/ipsd")
    parser.add_argument("--iscas-dir", default="data/benchmarks/iscas")
    parser.add_argument("--out-dir",   default="data/benchmarks")
    args = parser.parse_args()

    reader = CIFReader()
    writer = CIFWriter()

    for src_dir, subdir in [
        (args.ipsd_dir,  "ipsd"),
        (args.iscas_dir, "iscas"),
    ]:
        if not os.path.isdir(src_dir):
            continue
        out_subdir = os.path.join(args.out_dir, subdir + "_norm")
        os.makedirs(out_subdir, exist_ok=True)
        for fname in os.listdir(src_dir):
            if not fname.endswith(".cif"):
                continue
            src = os.path.join(src_dir, fname)
            dst = os.path.join(out_subdir, fname)
            try:
                layout = reader.read(src)
                warnings = validate_layout(layout)
                for w in warnings:
                    logger.warning("%s: %s", fname, w)
                layout = normalize_layout(layout)
                writer.write(layout, dst)
                logger.info("Normalized %s -> %s", src, dst)
            except Exception as exc:
                logger.error("Failed to normalize %s: %s", src, exc)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
