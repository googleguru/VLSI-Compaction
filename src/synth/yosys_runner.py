"""
Yosys synthesis runner.

Invokes Yosys to synthesize RTL Verilog or gate-level netlists, optionally
technology-mapping to a Liberty library.  Yosys is used solely as a
synthesis/netlist front-end; it does NOT perform layout compaction.

Typical flow
------------
1. read_verilog <input.v>
2. hierarchy -check -top <top>
3. proc; opt; techmap; opt
4. (if liberty) dfflibmap -liberty <lib.lib>; abc -liberty <lib.lib>
5. stat -liberty <lib.lib>  (or stat)
6. write_verilog <out.v>
"""

import os
import re
import shutil
import logging
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .liberty_handler import LibertyHandler

logger = logging.getLogger(__name__)


@dataclass
class SynthStats:
    top_module:    str = ""
    num_cells:     int = 0
    num_wires:     int = 0
    num_memories:  int = 0
    num_processes: int = 0
    cell_counts:   Dict[str, int] = field(default_factory=dict)
    chip_area:     float = 0.0       # from Liberty mapping; 0 if unavailable
    netlist_path:  str = ""
    log_path:      str = ""
    success:       bool = False
    error_message: str = ""


class YosysRunner:
    """
    Thin Python wrapper around the Yosys synthesis tool.

    Parameters
    ----------
    yosys_bin : str
        Path to the yosys executable.  Defaults to 'yosys' (PATH lookup).
    timeout : int
        Maximum synthesis time in seconds.
    """

    def __init__(
        self,
        yosys_bin: str = "yosys",
        timeout: int = 300,
    ):
        self.yosys_bin = yosys_bin
        self.timeout   = timeout
        self._available = shutil.which(yosys_bin) is not None

    @property
    def available(self) -> bool:
        return self._available

    def synthesize(
        self,
        verilog_path: str,
        out_dir: str,
        top_module: Optional[str] = None,
        liberty_path: Optional[str] = None,
    ) -> SynthStats:
        """
        Run Yosys synthesis on *verilog_path*.

        Parameters
        ----------
        verilog_path : str
            Input RTL or gate-level Verilog.
        out_dir : str
            Directory for output netlist and log.
        top_module : str | None
            Top-level module name.  If None, Yosys auto-detects.
        liberty_path : str | None
            Path to Liberty (.lib) file for technology mapping.

        Returns
        -------
        SynthStats with synthesis results.
        """
        os.makedirs(out_dir, exist_ok=True)
        base   = os.path.splitext(os.path.basename(verilog_path))[0]
        netlist_path = os.path.join(out_dir, f"{base}_synth.v")
        log_path     = os.path.join(out_dir, f"{base}_synth.log")

        stats = SynthStats(
            top_module   = top_module or "",
            netlist_path = netlist_path,
            log_path     = log_path,
        )

        if not self._available:
            logger.warning(
                "Yosys not found at '%s'. Synthesis skipped; "
                "demo geometry will use synthetic cell templates.",
                self.yosys_bin,
            )
            stats.error_message = "yosys not installed"
            return stats

        if not os.path.isfile(verilog_path):
            stats.error_message = f"input file not found: {verilog_path}"
            return stats

        lib_handler = LibertyHandler(liberty_path) if liberty_path else None
        script = self._build_script(
            verilog_path, netlist_path,
            top_module=top_module,
            lib_handler=lib_handler,
        )

        try:
            proc = subprocess.run(
                [self.yosys_bin, "-p", script],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            log_text = proc.stdout + proc.stderr
            with open(log_path, "w") as fh:
                fh.write(log_text)

            if proc.returncode != 0:
                stats.error_message = f"Yosys exited with code {proc.returncode}"
                logger.error("Yosys failed: %s", stats.error_message)
                return stats

            stats = self._parse_stats(log_text, stats)
            stats.success = True
            logger.info(
                "Synthesis complete: top=%s cells=%d area=%.1f → %s",
                stats.top_module, stats.num_cells, stats.chip_area, netlist_path,
            )

        except subprocess.TimeoutExpired:
            stats.error_message = f"Yosys timed out after {self.timeout}s"
            logger.error(stats.error_message)
        except FileNotFoundError:
            stats.error_message = f"Yosys binary not executable: {self.yosys_bin}"
            logger.error(stats.error_message)

        return stats

    # ── private ───────────────────────────────────────────────────────────────

    def _build_script(
        self,
        verilog_path: str,
        netlist_path: str,
        top_module: Optional[str],
        lib_handler: Optional["LibertyHandler"],
    ) -> str:
        top_flag = f"-top {top_module}" if top_module else ""
        lines = [
            f"read_verilog {verilog_path}",
            f"hierarchy -check {top_flag}",
            "proc",
            "opt",
            "techmap",
            "opt",
        ]
        if lib_handler and lib_handler.available:
            lp = lib_handler.path
            lines += [
                f"dfflibmap -liberty {lp}",
                f"abc -liberty {lp}",
                f"stat -liberty {lp}",
            ]
        else:
            lines.append("stat")

        lines.append(f"write_verilog {netlist_path}")
        return "; ".join(lines)

    def _parse_stats(self, log: str, stats: SynthStats) -> SynthStats:
        # Top module
        m = re.search(r"Hierarchy check passed\.\s+Top module:\s+(\S+)", log)
        if not m:
            m = re.search(r"Top module:\s+\\?(\S+)", log)
        if m:
            stats.top_module = m.group(1).lstrip("\\")

        # Number of cells from stat block
        m = re.search(r"Number of cells:\s+(\d+)", log)
        if m:
            stats.num_cells = int(m.group(1))

        m = re.search(r"Number of wires:\s+(\d+)", log)
        if m:
            stats.num_wires = int(m.group(1))

        # Chip area from Liberty stat
        m = re.search(r"Chip area for.*?:\s+([\d.]+)", log)
        if m:
            stats.chip_area = float(m.group(1))

        # Per-cell counts from stat block lines like "  NAND2  3"
        for line in log.splitlines():
            cm = re.match(r"\s{4,}(\w+)\s+(\d+)\s*$", line)
            if cm:
                stats.cell_counts[cm.group(1)] = int(cm.group(2))

        return stats
