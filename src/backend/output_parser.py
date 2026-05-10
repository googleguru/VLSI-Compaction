"""
Parse metadata from cellCompaction.pl stdout/stderr and output CIF.
Extracts iteration counts, shrink factors, and geometry summaries.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CompactionMetadata:
    iterations_run: int = 0
    xshrf_used: float = 1.0
    yshrf_used: float = 1.0
    runtime_seconds: float = 0.0
    backend_warnings: List[str] = field(default_factory=list)
    raw_stdout: str = ""
    raw_stderr: str = ""


_ITER_RE   = re.compile(r"iter(?:ation)?\s*[=:]\s*(\d+)", re.IGNORECASE)
_XSHRF_RE  = re.compile(r"[Xx]shrf\s*[=:]\s*([0-9.]+)")
_YSHRF_RE  = re.compile(r"[Yy]shrf\s*[=:]\s*([0-9.]+)")
_WARN_RE   = re.compile(r"(?:WARNING|WARN|Error):\s*(.*)", re.IGNORECASE)


def parse_backend_output(stdout: str, stderr: str, runtime: float) -> CompactionMetadata:
    meta = CompactionMetadata(runtime_seconds=runtime, raw_stdout=stdout, raw_stderr=stderr)

    combined = stdout + "\n" + stderr

    m = _ITER_RE.search(combined)
    if m:
        meta.iterations_run = int(m.group(1))

    m = _XSHRF_RE.search(combined)
    if m:
        meta.xshrf_used = float(m.group(1))

    m = _YSHRF_RE.search(combined)
    if m:
        meta.yshrf_used = float(m.group(1))

    for line in combined.splitlines():
        wm = _WARN_RE.search(line)
        if wm:
            meta.backend_warnings.append(wm.group(1).strip())

    return meta
