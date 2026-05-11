"""
Magic VLSI batch-mode runner.

Wraps Magic in non-interactive batch mode to perform:
  - CIF → Magic .mag conversion
  - Magic .mag → CIF conversion
  - CIF / .mag → GDS2 export
  - Design Rule Check (DRC) with violation count
  - Bounding-box extraction
  - PostScript / PNG layout rendering

Magic is invoked as:
    magic -dnull -noconsole -T <tech> < <tcl_script>

All operations degrade gracefully when Magic is not on PATH; the caller
receives a result object with success=False and an informative message.

Note: Magic does NOT perform layout compaction.  It is used here solely as a
layout I/O, DRC, and rendering tool.
"""

import os
import re
import shutil
import logging
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class MagicDRCResult:
    violations: int = 0
    success:    bool = False
    error:      str  = ""
    log:        str  = ""


@dataclass
class MagicBBoxResult:
    x0: int = 0
    y0: int = 0
    x1: int = 0
    y1: int = 0
    width:  int = 0
    height: int = 0
    success: bool = False
    error:   str  = ""


@dataclass
class MagicConvertResult:
    out_path: str  = ""
    success:  bool = False
    error:    str  = ""


class MagicRunner:
    """
    Thin Python wrapper around Magic VLSI batch mode.

    Parameters
    ----------
    magic_bin : str
        Path or name of the magic executable.
    tech : str
        Technology name passed to -T flag (e.g. 'scmos', 'sky130A').
    timeout : int
        Per-operation timeout in seconds.
    """

    def __init__(
        self,
        magic_bin: str = "magic",
        tech: str = "scmos",
        timeout: int = 120,
    ):
        self.magic_bin = magic_bin
        self.tech      = tech
        self.timeout   = timeout
        self._available = shutil.which(magic_bin) is not None
        if self._available:
            logger.info("Magic found: %s (tech=%s)", shutil.which(magic_bin), tech)
        else:
            logger.info("Magic not found at '%s'; layout DRC/export will be skipped.", magic_bin)

    @property
    def available(self) -> bool:
        return self._available

    # ── format conversion ─────────────────────────────────────────────────────

    def cif_to_mag(self, cif_path: str, out_dir: str) -> MagicConvertResult:
        """
        Convert a CIF file to Magic .mag format.

        Returns MagicConvertResult with out_path = <out_dir>/<stem>.mag
        """
        os.makedirs(out_dir, exist_ok=True)
        stem     = os.path.splitext(os.path.basename(cif_path))[0]
        out_path = os.path.join(out_dir, f"{stem}.mag")

        script = f"""\
cif read {cif_path}
save {os.path.join(out_dir, stem)}
quit
"""
        return self._run_script(script, out_path)

    def mag_to_cif(self, mag_path: str, out_dir: str) -> MagicConvertResult:
        """Convert a Magic .mag file back to CIF."""
        os.makedirs(out_dir, exist_ok=True)
        stem     = os.path.splitext(os.path.basename(mag_path))[0]
        out_path = os.path.join(out_dir, f"{stem}.cif")

        script = f"""\
load {mag_path}
cif write {out_path}
quit
"""
        return self._run_script(script, out_path)

    def cif_to_gds(self, cif_path: str, out_dir: str) -> MagicConvertResult:
        """
        Convert CIF to GDS2 via Magic.
        GDS2 is the industry-standard layout interchange format.
        """
        os.makedirs(out_dir, exist_ok=True)
        stem     = os.path.splitext(os.path.basename(cif_path))[0]
        out_path = os.path.join(out_dir, f"{stem}.gds")

        script = f"""\
cif read {cif_path}
gds write {out_path}
quit
"""
        return self._run_script(script, out_path)

    def mag_to_gds(self, mag_path: str, out_dir: str) -> MagicConvertResult:
        """Convert Magic .mag to GDS2."""
        os.makedirs(out_dir, exist_ok=True)
        stem     = os.path.splitext(os.path.basename(mag_path))[0]
        out_path = os.path.join(out_dir, f"{stem}.gds")

        script = f"""\
load {mag_path}
gds write {out_path}
quit
"""
        return self._run_script(script, out_path)

    # ── DRC ───────────────────────────────────────────────────────────────────

    def run_drc_on_cif(self, cif_path: str) -> MagicDRCResult:
        """
        Load a CIF file into Magic and run DRC.

        Returns MagicDRCResult with violation count.
        When Magic is unavailable returns success=False so callers can fall
        back to the geometry overlap estimator.
        """
        if not self._available:
            return MagicDRCResult(error="magic not installed")

        stem   = os.path.splitext(os.path.basename(cif_path))[0]
        script = f"""\
cif read {cif_path}
drc check
set n [drc count]
puts "MAGIC_DRC_COUNT $n"
quit
"""
        log = self._run_raw(script)
        return self._parse_drc(log)

    def run_drc_on_mag(self, mag_path: str) -> MagicDRCResult:
        """Load a .mag file and run DRC."""
        if not self._available:
            return MagicDRCResult(error="magic not installed")

        stem   = os.path.splitext(os.path.basename(mag_path))[0]
        script = f"""\
load {mag_path}
drc check
set n [drc count]
puts "MAGIC_DRC_COUNT $n"
quit
"""
        log = self._run_raw(script)
        return self._parse_drc(log)

    # ── bounding box ─────────────────────────────────────────────────────────

    def get_bbox_cif(self, cif_path: str) -> MagicBBoxResult:
        """Extract bounding box from a CIF file via Magic."""
        if not self._available:
            return MagicBBoxResult(error="magic not installed")

        script = f"""\
cif read {cif_path}
select top cell
set b [box]
puts "MAGIC_BBOX $b"
quit
"""
        log = self._run_raw(script)
        return self._parse_bbox(log)

    # ── rendering ─────────────────────────────────────────────────────────────

    def render_cif_to_ps(self, cif_path: str, out_dir: str) -> MagicConvertResult:
        """
        Render a CIF layout to PostScript using Magic's plot command.
        Convert to PNG with Ghostscript if available.
        """
        os.makedirs(out_dir, exist_ok=True)
        stem    = os.path.splitext(os.path.basename(cif_path))[0]
        ps_path = os.path.join(out_dir, f"{stem}_magic.ps")

        script = f"""\
cif read {cif_path}
select top cell
plot postscript {ps_path}
quit
"""
        result = self._run_script(script, ps_path)
        if result.success and shutil.which("gs"):
            png_path = ps_path.replace(".ps", ".png")
            try:
                subprocess.run(
                    ["gs", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                     "-sDEVICE=png16m", "-r150",
                     f"-sOutputFile={png_path}", ps_path],
                    capture_output=True, timeout=60,
                )
                result.out_path = png_path
            except Exception as exc:
                logger.debug("Ghostscript PNG conversion failed: %s", exc)
        return result

    def render_mag_to_ps(self, mag_path: str, out_dir: str) -> MagicConvertResult:
        """Render a .mag layout to PostScript / PNG."""
        os.makedirs(out_dir, exist_ok=True)
        stem    = os.path.splitext(os.path.basename(mag_path))[0]
        ps_path = os.path.join(out_dir, f"{stem}_magic.ps")

        script = f"""\
load {mag_path}
select top cell
plot postscript {ps_path}
quit
"""
        result = self._run_script(script, ps_path)
        if result.success and shutil.which("gs"):
            png_path = ps_path.replace(".ps", ".png")
            try:
                subprocess.run(
                    ["gs", "-dNOPAUSE", "-dBATCH", "-dSAFER",
                     "-sDEVICE=png16m", "-r150",
                     f"-sOutputFile={png_path}", ps_path],
                    capture_output=True, timeout=60,
                )
                result.out_path = png_path
            except Exception as exc:
                logger.debug("Ghostscript PNG conversion failed: %s", exc)
        return result

    # ── private helpers ───────────────────────────────────────────────────────

    def _run_script(self, script: str, expected_output: str) -> MagicConvertResult:
        """Run a Magic TCL script and check whether expected_output was created."""
        if not self._available:
            return MagicConvertResult(
                error="magic not installed",
                out_path=expected_output,
            )
        log = self._run_raw(script)
        if os.path.isfile(expected_output):
            return MagicConvertResult(out_path=expected_output, success=True)
        return MagicConvertResult(
            out_path=expected_output,
            error=f"output not created; magic log: {log[-500:]}",
        )

    def _run_raw(self, script: str) -> str:
        """Invoke magic -dnull -noconsole -T <tech> and pipe script to stdin."""
        cmd = [self.magic_bin, "-dnull", "-noconsole", "-T", self.tech]
        try:
            proc = subprocess.run(
                cmd,
                input=script,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            return proc.stdout + proc.stderr
        except subprocess.TimeoutExpired:
            return f"TIMEOUT after {self.timeout}s"
        except FileNotFoundError:
            return "ERROR: magic binary not found"

    @staticmethod
    def _parse_drc(log: str) -> MagicDRCResult:
        m = re.search(r"MAGIC_DRC_COUNT\s+(\d+)", log)
        if m:
            return MagicDRCResult(violations=int(m.group(1)), success=True, log=log)
        # Also accept Magic's own "N DRC errors found" output
        m2 = re.search(r"(\d+)\s+DRC error", log, re.IGNORECASE)
        if m2:
            return MagicDRCResult(violations=int(m2.group(1)), success=True, log=log)
        return MagicDRCResult(
            success=False,
            error="DRC count not found in Magic output",
            log=log,
        )

    @staticmethod
    def _parse_bbox(log: str) -> MagicBBoxResult:
        # Magic box output: "x1 y1 x2 y2" or "{x1 y1 x2 y2}"
        m = re.search(
            r"MAGIC_BBOX\s+\{?(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\}?", log
        )
        if m:
            x0, y0, x1, y1 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
            return MagicBBoxResult(
                x0=x0, y0=y0, x1=x1, y1=y1,
                width=x1 - x0, height=y1 - y0,
                success=True,
            )
        return MagicBBoxResult(error="bbox not found in Magic output")
