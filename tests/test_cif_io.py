"""
Tests for CIF reader and writer round-trip correctness.
"""

import textwrap
import pytest
from src.io.cif_reader import CIFReader, CIFBox, CIFPolygon
from src.io.cif_writer import CIFWriter


SIMPLE_CIF = textwrap.dedent("""\
    (Test layout)
    DS 1 1 2;
    9 test_cell;
    L POLY;
    B 100 80 50 40;
    L METAL1;
    P 0 0 200 0 200 100 0 100;
    DF;
    C 1;
    E
""")


def test_reader_parses_box():
    reader = CIFReader()
    layout = reader.read_string(SIMPLE_CIF)
    assert 1 in layout.symbols
    sym = layout.symbols[1]
    assert len(sym.boxes) == 1
    box = sym.boxes[0]
    assert box.layer == "POLY"
    assert box.width == 100
    assert box.height == 80
    assert box.cx == 50
    assert box.cy == 40


def test_reader_parses_polygon():
    reader = CIFReader()
    layout = reader.read_string(SIMPLE_CIF)
    sym = layout.symbols[1]
    assert len(sym.polygons) == 1
    poly = sym.polygons[0]
    assert poly.layer == "METAL1"
    assert len(poly.points) == 4


def test_reader_top_call():
    reader = CIFReader()
    layout = reader.read_string(SIMPLE_CIF)
    assert len(layout.top_calls) == 1
    assert layout.top_calls[0].symbol_num == 1


def test_writer_round_trip():
    reader = CIFReader()
    writer = CIFWriter()
    layout = reader.read_string(SIMPLE_CIF)
    out    = writer.write_string(layout)
    layout2 = reader.read_string(out)
    assert 1 in layout2.symbols
    assert len(layout2.symbols[1].boxes) == 1
    assert layout2.symbols[1].boxes[0].width == 100


def test_bbox_computation():
    reader = CIFReader()
    layout = reader.read_string(SIMPLE_CIF)
    bbox = layout.geometry_bbox()
    assert bbox[2] > bbox[0]
    assert bbox[3] > bbox[1]


def test_symbol_name_parsed():
    reader = CIFReader()
    layout = reader.read_string(SIMPLE_CIF)
    assert layout.symbols[1].name == "test_cell"


def test_empty_cif():
    reader = CIFReader()
    layout = reader.read_string("E\n")
    assert len(layout.symbols) == 0
    assert len(layout.top_calls) == 0
