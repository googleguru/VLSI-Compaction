"""
CIF layout file writer.
Emits well-formed CIF from a CIFLayout object.
"""

from typing import TextIO
from .cif_reader import CIFLayout, CIFSymbol, CIFBox, CIFPolygon, CIFWire, CIFCall


class CIFWriter:
    def write(self, layout: CIFLayout, path: str) -> None:
        with open(path, "w") as fh:
            self._emit(layout, fh)

    def write_string(self, layout: CIFLayout) -> str:
        from io import StringIO
        buf = StringIO()
        self._emit(layout, buf)
        return buf.getvalue()

    def _emit(self, layout: CIFLayout, fh: TextIO) -> None:
        for comment in layout.comments:
            fh.write(f"({comment})\n")

        for sym in layout.symbols.values():
            self._write_symbol(sym, fh)

        for call in layout.top_calls:
            self._write_call(call, fh)

        fh.write("E\n")

    def _write_symbol(self, sym: CIFSymbol, fh: TextIO) -> None:
        fh.write(f"DS {sym.number} {sym.scale_a} {sym.scale_b};\n")
        if sym.name:
            fh.write(f"9 {sym.name};\n")

        current_layer = ""
        all_geom = (
            [("box", b) for b in sym.boxes]
            + [("poly", p) for p in sym.polygons]
            + [("wire", w) for w in sym.wires]
        )
        for kind, geom in all_geom:
            if geom.layer != current_layer:
                current_layer = geom.layer
                fh.write(f"L {current_layer};\n")
            if kind == "box":
                fh.write(f"B {geom.width} {geom.height} {geom.cx} {geom.cy};\n")
            elif kind == "poly":
                pts = " ".join(f"{x} {y}" for x, y in geom.points)
                fh.write(f"P {pts};\n")
            elif kind == "wire":
                pts = " ".join(f"{x} {y}" for x, y in geom.points)
                fh.write(f"W {geom.width} {pts};\n")

        for call in sym.calls:
            self._write_call(call, fh)

        fh.write("DF;\n")

    def _write_call(self, call: CIFCall, fh: TextIO) -> None:
        if call.tx != 0 or call.ty != 0:
            fh.write(f"C {call.symbol_num} T {call.tx} {call.ty};\n")
        else:
            fh.write(f"C {call.symbol_num};\n")
