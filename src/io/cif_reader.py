"""
CIF (Caltech Intermediate Form) layout file reader.
Supports DS/DF, B, P, W, L, C, and 9 (comment) commands.
"""

import re
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict


@dataclass
class CIFBox:
    layer: str
    width: int
    height: int
    cx: int
    cy: int

    def bbox(self) -> Tuple[int, int, int, int]:
        hw, hh = self.width // 2, self.height // 2
        return self.cx - hw, self.cy - hh, self.cx + hw, self.cy + hh


@dataclass
class CIFPolygon:
    layer: str
    points: List[Tuple[int, int]]

    def bbox(self) -> Tuple[int, int, int, int]:
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        return min(xs), min(ys), max(xs), max(ys)


@dataclass
class CIFWire:
    layer: str
    width: int
    points: List[Tuple[int, int]]

    def bbox(self) -> Tuple[int, int, int, int]:
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        hw = self.width // 2
        return min(xs) - hw, min(ys) - hw, max(xs) + hw, max(ys) + hw


@dataclass
class CIFCall:
    symbol_num: int
    tx: int = 0
    ty: int = 0


@dataclass
class CIFSymbol:
    number: int
    scale_a: int = 1
    scale_b: int = 2
    name: str = ""
    boxes: List[CIFBox] = field(default_factory=list)
    polygons: List[CIFPolygon] = field(default_factory=list)
    wires: List[CIFWire] = field(default_factory=list)
    calls: List[CIFCall] = field(default_factory=list)


@dataclass
class CIFLayout:
    symbols: Dict[int, CIFSymbol] = field(default_factory=dict)
    top_calls: List[CIFCall] = field(default_factory=list)
    comments: List[str] = field(default_factory=list)

    def geometry_bbox(self) -> Tuple[int, int, int, int]:
        """Compute bounding box of all top-level geometry."""
        all_boxes = self._collect_all_geometry()
        if not all_boxes:
            return (0, 0, 0, 0)
        x0 = min(b[0] for b in all_boxes)
        y0 = min(b[1] for b in all_boxes)
        x1 = max(b[2] for b in all_boxes)
        y1 = max(b[3] for b in all_boxes)
        return x0, y0, x1, y1

    def _collect_all_geometry(self) -> List[Tuple[int, int, int, int]]:
        # Use top-level calls (with their translations) when present;
        # fall back to direct symbol traversal for CIF files with no top calls.
        bboxes = []
        if self.top_calls:
            for call in self.top_calls:
                sym = self.symbols.get(call.symbol_num)
                if sym:
                    bboxes.extend(self._symbol_bboxes(sym, call.tx, call.ty))
        else:
            for sym in self.symbols.values():
                bboxes.extend(self._symbol_bboxes(sym, 0, 0))
        return bboxes

    def _symbol_bboxes(
        self, sym: CIFSymbol, dx: int, dy: int
    ) -> List[Tuple[int, int, int, int]]:
        result = []
        for b in sym.boxes:
            x0, y0, x1, y1 = b.bbox()
            result.append((x0 + dx, y0 + dy, x1 + dx, y1 + dy))
        for p in sym.polygons:
            x0, y0, x1, y1 = p.bbox()
            result.append((x0 + dx, y0 + dy, x1 + dx, y1 + dy))
        for w in sym.wires:
            x0, y0, x1, y1 = w.bbox()
            result.append((x0 + dx, y0 + dy, x1 + dx, y1 + dy))
        for c in sym.calls:
            child = self.symbols.get(c.symbol_num)
            if child:
                result.extend(
                    self._symbol_bboxes(child, dx + c.tx, dy + c.ty)
                )
        return result


class CIFReader:
    _DS_RE = re.compile(r"DS\s+(\d+)\s+(\d+)\s+(\d+)")
    _B_RE  = re.compile(r"B\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)")
    _P_RE  = re.compile(r"P\s+((?:-?\d+\s*)+)")
    _W_RE  = re.compile(r"W\s+(-?\d+)\s+((?:-?\d+\s*)+)")
    _C_RE  = re.compile(r"C\s+(\d+)(?:\s+T\s+(-?\d+)\s+(-?\d+))?")
    _L_RE  = re.compile(r"L\s+(\w+)")
    _N_RE  = re.compile(r"9\s+(.*)")

    def read(self, path: str) -> CIFLayout:
        with open(path, "r") as fh:
            raw = fh.read()
        tokens = self._tokenize(raw)
        return self._parse(tokens)

    def read_string(self, text: str) -> CIFLayout:
        tokens = self._tokenize(text)
        return self._parse(tokens)

    def _tokenize(self, raw: str) -> List[str]:
        # Strip block comments (parentheses), then split on semicolons
        text = re.sub(r"\([^)]*\)", " ", raw)
        commands = [c.strip() for c in text.split(";") if c.strip()]
        return commands

    def _parse(self, commands: List[str]) -> CIFLayout:
        layout = CIFLayout()
        current_sym: Optional[CIFSymbol] = None
        current_layer = ""

        for cmd in commands:
            cmd = cmd.strip()
            if not cmd or cmd == "E":
                if cmd == "E":
                    break
                continue

            m = self._DS_RE.match(cmd)
            if m:
                n, a, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
                current_sym = CIFSymbol(number=n, scale_a=a, scale_b=b)
                current_layer = ""
                continue

            if cmd.startswith("DF"):
                if current_sym is not None:
                    layout.symbols[current_sym.number] = current_sym
                    current_sym = None
                continue

            m = self._L_RE.match(cmd)
            if m:
                current_layer = m.group(1)
                continue

            m = self._N_RE.match(cmd)
            if m:
                name = m.group(1).strip()
                if current_sym is not None:
                    current_sym.name = name
                else:
                    layout.comments.append(name)
                continue

            m = self._B_RE.match(cmd)
            if m:
                w, h, cx, cy = (
                    int(m.group(1)), int(m.group(2)),
                    int(m.group(3)), int(m.group(4)),
                )
                box = CIFBox(layer=current_layer, width=w, height=h, cx=cx, cy=cy)
                if current_sym is not None:
                    current_sym.boxes.append(box)
                continue

            m = self._P_RE.match(cmd)
            if m:
                nums = list(map(int, m.group(1).split()))
                points = [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
                poly = CIFPolygon(layer=current_layer, points=points)
                if current_sym is not None:
                    current_sym.polygons.append(poly)
                continue

            m = self._W_RE.match(cmd)
            if m:
                width = int(m.group(1))
                nums = list(map(int, m.group(2).split()))
                points = [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
                wire = CIFWire(layer=current_layer, width=width, points=points)
                if current_sym is not None:
                    current_sym.wires.append(wire)
                continue

            m = self._C_RE.match(cmd)
            if m:
                sym_num = int(m.group(1))
                tx = int(m.group(2)) if m.group(2) else 0
                ty = int(m.group(3)) if m.group(3) else 0
                call = CIFCall(symbol_num=sym_num, tx=tx, ty=ty)
                if current_sym is not None:
                    current_sym.calls.append(call)
                else:
                    layout.top_calls.append(call)
                continue

        return layout
