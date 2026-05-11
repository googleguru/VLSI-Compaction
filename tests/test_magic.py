"""
Tests for Magic VLSI integration.

Covers:
  - MagReader:   parse .mag files, subcell resolution, CIF conversion
  - MagWriter:   write flat + hierarchical .mag files
  - TechHandler: layer map resolution for scmos / sky130A
  - MagicRunner: availability check, graceful fallback when Magic absent
  - layout_plotter: Magic-style palette + hatch rendering (no display)

All tests pass without Magic installed.
"""

import os
import tempfile
import textwrap

import pytest

from src.io.mag_reader import MagReader, read_mag
from src.io.mag_writer import MagWriter, write_mag_flat
from src.io.cif_reader import CIFLayout, CIFSymbol, CIFBox, CIFCall
from src.layout.tech_handler import TechHandler, LayerMap
from src.layout.magic_runner import MagicRunner, MagicDRCResult


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_mag(content: str) -> str:
    """Write content to a temp .mag file; returns the path."""
    fd, path = tempfile.mkstemp(suffix=".mag")
    with os.fdopen(fd, "w") as fh:
        fh.write(textwrap.dedent(content))
    return path


def _simple_layout() -> CIFLayout:
    layout = CIFLayout()
    sym = CIFSymbol(number=1, name="cell_a")
    sym.boxes.append(CIFBox(layer="POLY", width=10, height=20, cx=5, cy=10))
    sym.boxes.append(CIFBox(layer="METAL1", width=8, height=4, cx=20, cy=2))
    layout.symbols[1] = sym
    layout.top_calls.append(CIFCall(symbol_num=1, tx=0, ty=0))
    return layout


# ── TechHandler ───────────────────────────────────────────────────────────────

class TestTechHandler:
    def test_scmos_layer_map_returns_layermap(self):
        th = TechHandler("scmos")
        lm = th.layer_map()
        assert isinstance(lm, LayerMap)

    def test_poly_resolves_scmos(self):
        lm = TechHandler("scmos").layer_map()
        assert lm.resolve("POLY") == "poly"

    def test_metal1_resolves_scmos(self):
        lm = TechHandler("scmos").layer_map()
        assert lm.resolve("METAL1") == "metal1"

    def test_contact_aliases(self):
        lm = TechHandler("scmos").layer_map()
        assert lm.resolve("CONT") == "contact"

    def test_sky130_poly(self):
        lm = TechHandler("sky130A").layer_map()
        assert lm.resolve("POLY") == "poly"

    def test_sky130_metal_layers(self):
        lm = TechHandler("sky130A").layer_map()
        assert lm.resolve("MET1") == "met1"

    def test_unknown_layer_returns_lowercased(self):
        lm = TechHandler("scmos").layer_map()
        result = lm.resolve("UNKNOWN_LAYER_XYZ")
        assert result == "unknown_layer_xyz"

    def test_case_insensitive_lookup(self):
        lm = TechHandler("scmos").layer_map()
        assert lm.resolve("poly") == lm.resolve("POLY")

    def test_gf180_layer_map(self):
        lm = TechHandler("gf180mcu").layer_map()
        assert lm.resolve("POLY") in ("poly2", "poly")


# ── MagReader ─────────────────────────────────────────────────────────────────

class TestMagReader:
    def test_parse_simple_mag(self):
        path = _make_mag("""\
            magic
            tech scmos
            timestamp 1234567890
            << poly >>
            rect 0 0 10 20
            << metal1 >>
            rect 5 5 15 25
            << end >>
        """)
        try:
            layout = read_mag(path)
            # Should produce at least 2 symbols (one per layer)
            assert len(layout.symbols) >= 2
        finally:
            os.unlink(path)

    def test_rect_converted_to_cifbox(self):
        path = _make_mag("""\
            magic
            tech scmos
            timestamp 1
            << poly >>
            rect 0 0 100 200
            << end >>
        """)
        try:
            layout = read_mag(path)
            sym = next(iter(layout.symbols.values()))
            assert len(sym.boxes) == 1
            box = sym.boxes[0]
            assert box.width == 100
            assert box.height == 200
            assert box.cx == 50
            assert box.cy == 100
        finally:
            os.unlink(path)

    def test_layer_name_uppercased_in_cifbox(self):
        path = _make_mag("""\
            magic
            tech scmos
            timestamp 1
            << metal2 >>
            rect 0 0 4 4
            << end >>
        """)
        try:
            layout = read_mag(path)
            sym = next(iter(layout.symbols.values()))
            assert sym.boxes[0].layer == "METAL2"
        finally:
            os.unlink(path)

    def test_top_calls_created(self):
        path = _make_mag("""\
            magic
            tech scmos
            timestamp 1
            << poly >>
            rect 0 0 10 10
            << end >>
        """)
        try:
            layout = read_mag(path)
            assert len(layout.top_calls) >= 1
        finally:
            os.unlink(path)

    def test_scale_applied(self):
        path = _make_mag("""\
            magic
            tech scmos
            timestamp 1
            << poly >>
            rect 0 0 10 20
            << end >>
        """)
        try:
            layout = read_mag(path, scale=100)
            sym = next(iter(layout.symbols.values()))
            box = sym.boxes[0]
            assert box.width == 1000
            assert box.height == 2000
        finally:
            os.unlink(path)

    def test_subcell_resolution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sub_path = os.path.join(tmpdir, "sub.mag")
            with open(sub_path, "w") as fh:
                fh.write("magic\ntech scmos\ntimestamp 1\n<< metal1 >>\nrect 0 0 5 5\n<< end >>\n")

            top_path = os.path.join(tmpdir, "top.mag")
            with open(top_path, "w") as fh:
                fh.write("magic\ntech scmos\ntimestamp 1\n"
                         "<< poly >>\nrect 0 0 10 10\n"
                         "<< subcells >>\nuse sub sub_i1\narray 1 1 1 1 20 0 0 0\n"
                         "timestamp 1\n<< end >>\n")

            layout = read_mag(top_path)
            layers = {b.layer for sym in layout.symbols.values() for b in sym.boxes}
            assert "POLY" in layers
            assert "METAL1" in layers

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            read_mag("/tmp/nonexistent_magic_file_xyz.mag")

    def test_multiple_rects_same_layer(self):
        path = _make_mag("""\
            magic
            tech scmos
            timestamp 1
            << metal1 >>
            rect 0 0 10 10
            rect 20 20 30 30
            << end >>
        """)
        try:
            layout = read_mag(path)
            sym = next(iter(layout.symbols.values()))
            assert len(sym.boxes) == 2
        finally:
            os.unlink(path)


# ── MagWriter ─────────────────────────────────────────────────────────────────

class TestMagWriter:
    def test_write_flat_creates_file(self):
        layout = _simple_layout()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "flat.mag")
            result = write_mag_flat(layout, out_path, tech="scmos")
            assert os.path.isfile(result)

    def test_write_flat_contains_magic_header(self):
        layout = _simple_layout()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "flat.mag")
            write_mag_flat(layout, out_path, tech="scmos")
            content = open(out_path).read()
            assert content.startswith("magic\n")
            assert "tech scmos" in content

    def test_write_flat_contains_rect(self):
        layout = _simple_layout()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "flat.mag")
            write_mag_flat(layout, out_path, tech="scmos")
            content = open(out_path).read()
            assert "rect" in content

    def test_write_flat_contains_end_marker(self):
        layout = _simple_layout()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "flat.mag")
            write_mag_flat(layout, out_path)
            content = open(out_path).read()
            assert "<< end >>" in content

    def test_write_flat_layer_names_lowercased(self):
        layout = _simple_layout()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "flat.mag")
            write_mag_flat(layout, out_path, tech="scmos")
            content = open(out_path).read()
            # Magic layer names are lowercase in .mag files
            assert "POLY" not in content or "<< poly >>" in content

    def test_write_hierarchical_creates_top_file(self):
        layout = _simple_layout()
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = MagWriter(tech="scmos", top_name="mytop")
            top_path = writer.write(layout, tmpdir)
            assert os.path.isfile(top_path)
            assert os.path.basename(top_path) == "mytop.mag"

    def test_write_roundtrip_preserves_layer(self):
        layout = _simple_layout()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "rt.mag")
            write_mag_flat(layout, out_path, tech="scmos")
            layout2 = read_mag(out_path)
            layers2 = {b.layer for sym in layout2.symbols.values() for b in sym.boxes}
            assert len(layers2) >= 1

    def test_write_flat_scale(self):
        layout = CIFLayout()
        sym = CIFSymbol(number=1, name="s")
        sym.boxes.append(CIFBox(layer="POLY", width=1000, height=2000, cx=500, cy=1000))
        layout.symbols[1] = sym
        layout.top_calls.append(CIFCall(symbol_num=1, tx=0, ty=0))
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "scaled.mag")
            writer = MagWriter(tech="scmos", scale=100)
            writer.write_flat(layout, out_path)
            content = open(out_path).read()
            # After scaling by 100: width=10, so rect should be 0 0 10 20
            assert "rect 0 0 10 20" in content


# ── MagicRunner ───────────────────────────────────────────────────────────────

class TestMagicRunner:
    def test_available_property_is_bool(self):
        runner = MagicRunner()
        assert isinstance(runner.available, bool)

    def test_unavailable_runner_returns_failure_drc(self):
        runner = MagicRunner(magic_bin="__nonexistent_magic_bin__")
        assert not runner.available
        result = runner.run_drc_on_cif("/tmp/fake.cif")
        assert isinstance(result, MagicDRCResult)
        assert not result.success

    def test_unavailable_runner_drc_violations_zero(self):
        runner = MagicRunner(magic_bin="__nonexistent_magic_bin__")
        result = runner.run_drc_on_cif("/tmp/fake.cif")
        assert result.violations == 0

    def test_unavailable_cif_to_mag_returns_failure(self):
        runner = MagicRunner(magic_bin="__nonexistent_magic_bin__")
        result = runner.cif_to_mag("/tmp/fake.cif", "/tmp/outdir")
        assert not result.success

    def test_unavailable_cif_to_gds_returns_failure(self):
        runner = MagicRunner(magic_bin="__nonexistent_magic_bin__")
        result = runner.cif_to_gds("/tmp/fake.cif", "/tmp/fake.gds")
        assert not result.success

    def test_drc_result_has_error_when_unavailable(self):
        runner = MagicRunner(magic_bin="__nonexistent_magic_bin__")
        result = runner.run_drc_on_cif("/tmp/fake.cif")
        assert result.error is not None and len(result.error) > 0


# ── layout_plotter (Magic rendering, no display) ──────────────────────────────

class TestLayoutPlotter:
    def test_plot_magic_layout_returns_figure(self):
        import matplotlib
        matplotlib.use("Agg")
        from src.viz.layout_plotter import plot_magic_layout
        layout = _simple_layout()
        fig = plot_magic_layout(layout, title="test", tech="scmos")
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close("all")

    def test_plot_magic_layout_saves_file(self):
        import matplotlib
        matplotlib.use("Agg")
        from src.viz.layout_plotter import plot_magic_layout
        import matplotlib.pyplot as plt
        layout = _simple_layout()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "magic_layout.png")
            plot_magic_layout(layout, title="test", tech="scmos", out_path=out_path)
            assert os.path.isfile(out_path)
        plt.close("all")

    def test_plot_before_after_saves_file(self):
        import matplotlib
        matplotlib.use("Agg")
        from src.viz.layout_plotter import plot_before_after
        import matplotlib.pyplot as plt
        layout = _simple_layout()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = os.path.join(tmpdir, "before_after.png")
            plot_before_after(layout, layout, "test_bench", out_path, tech="scmos")
            assert os.path.isfile(out_path)
        plt.close("all")

    def test_sky130_palette_accepted(self):
        import matplotlib
        matplotlib.use("Agg")
        from src.viz.layout_plotter import plot_magic_layout
        import matplotlib.pyplot as plt
        layout = _simple_layout()
        fig = plot_magic_layout(layout, tech="sky130A")
        assert fig is not None
        plt.close("all")


# ── magic_drc_helper ─────────────────────────────────────────────────────────

class TestMagicDRCHelper:
    def test_fallback_when_magic_absent(self):
        from src.eval.magic_drc_helper import drc_violations
        from src.io.cif_reader import CIFLayout, CIFSymbol, CIFBox
        bboxes = [(0, 0, 10, 10), (5, 5, 15, 15)]  # overlapping
        count, used_magic = drc_violations(
            "/tmp/nonexistent.cif",
            bboxes,
            spacing_lambda=1,
            magic_runner=MagicRunner(magic_bin="__nonexistent__"),
        )
        assert not used_magic
        assert count >= 0

    def test_returns_int_count(self):
        from src.eval.magic_drc_helper import drc_violations
        count, _ = drc_violations(
            "/tmp/nonexistent.cif",
            [],
            magic_runner=MagicRunner(magic_bin="__nonexistent__"),
        )
        assert isinstance(count, int)
