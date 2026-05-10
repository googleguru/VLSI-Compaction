"""
Wrapper for the cellCompaction.pl Perl backend.

Calls:
  perl cellCompaction.pl -iter N -Xshrf a -Yshrf b -input in.cif -comp out.cif

The script path is resolved from configs/default.yaml or overridden directly.
"""

import os
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .command_runner import run_command, RunResult
from .output_parser import parse_backend_output, CompactionMetadata
from ..io.cif_reader import CIFReader, CIFLayout
from ..io.cif_writer import CIFWriter

logger = logging.getLogger(__name__)

_DEFAULT_SCRIPT_LOCATIONS = [
    "vendor/cellCompaction.pl",
    "Cell-Based-Layout-Compaction/cellCompaction.pl",
    "cellCompaction.pl",
]


@dataclass
class CompactionRequest:
    input_cif: str
    output_cif: str
    iterations: int = 5
    xshrf: float = 0.9
    yshrf: float = 0.9
    timeout: int = 300


@dataclass
class CompactionResult:
    ok: bool
    output_cif: str
    layout: Optional[CIFLayout]
    metadata: CompactionMetadata
    run_result: RunResult


class PerlCompactionWrapper:
    def __init__(self, script_path: Optional[str] = None, perl_exe: str = "perl"):
        self.perl_exe = perl_exe
        self.script_path = script_path or self._find_script()

    def _find_script(self) -> str:
        for loc in _DEFAULT_SCRIPT_LOCATIONS:
            if os.path.isfile(loc):
                return loc
        return _DEFAULT_SCRIPT_LOCATIONS[0]

    def is_available(self) -> bool:
        if not os.path.isfile(self.script_path):
            logger.warning(
                "cellCompaction.pl not found at %s. "
                "Clone the upstream repository into vendor/ or set script_path.",
                self.script_path,
            )
            return False
        if not shutil.which(self.perl_exe):
            logger.warning("perl not found in PATH")
            return False
        return True

    def run(self, req: CompactionRequest) -> CompactionResult:
        if not self.is_available():
            return self._unavailable_result(req)

        cmd = [
            self.perl_exe,
            self.script_path,
            "-iter", str(req.iterations),
            "-Xshrf", str(req.xshrf),
            "-Yshrf", str(req.yshrf),
            "-input", req.input_cif,
            "-comp", req.output_cif,
        ]

        run_result = run_command(cmd, timeout=req.timeout)
        meta = parse_backend_output(
            run_result.stdout, run_result.stderr, run_result.elapsed_seconds
        )
        meta.xshrf_used = req.xshrf
        meta.yshrf_used = req.yshrf
        meta.iterations_run = req.iterations

        layout = None
        if run_result.ok and os.path.isfile(req.output_cif):
            try:
                layout = CIFReader().read(req.output_cif)
            except Exception as exc:
                logger.error("Failed to parse output CIF %s: %s", req.output_cif, exc)

        return CompactionResult(
            ok=run_result.ok and layout is not None,
            output_cif=req.output_cif,
            layout=layout,
            metadata=meta,
            run_result=run_result,
        )

    def _unavailable_result(self, req: CompactionRequest) -> CompactionResult:
        from .command_runner import RunResult as RR
        dummy_run = RR(returncode=-3, stdout="", stderr="backend unavailable",
                       elapsed_seconds=0.0, command=[])
        meta = CompactionMetadata()
        meta.backend_warnings.append(
            "cellCompaction.pl not found. Populate vendor/ with the upstream Perl script."
        )
        return CompactionResult(
            ok=False,
            output_cif=req.output_cif,
            layout=None,
            metadata=meta,
            run_result=dummy_run,
        )
