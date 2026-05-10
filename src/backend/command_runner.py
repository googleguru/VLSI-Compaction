"""
Low-level subprocess runner for the Perl compaction backend.
Handles timeout, stdout/stderr capture, and exit-code checking.
"""

import subprocess
import logging
import time
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    returncode: int
    stdout: str
    stderr: str
    elapsed_seconds: float
    command: List[str]

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run_command(
    cmd: List[str],
    timeout: int = 300,
    cwd: Optional[str] = None,
) -> RunResult:
    logger.debug("Running: %s", " ".join(cmd))
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        elapsed = time.monotonic() - t0
        result = RunResult(
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            elapsed_seconds=elapsed,
            command=cmd,
        )
        if not result.ok:
            logger.warning(
                "Command returned %d: %s\nstderr: %s",
                proc.returncode, " ".join(cmd), proc.stderr[:500],
            )
        return result
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - t0
        logger.error("Command timed out after %ds: %s", timeout, " ".join(cmd))
        return RunResult(
            returncode=-1,
            stdout="",
            stderr=f"TIMEOUT after {timeout}s",
            elapsed_seconds=elapsed,
            command=cmd,
        )
    except FileNotFoundError as exc:
        logger.error("Executable not found: %s", exc)
        return RunResult(
            returncode=-2,
            stdout="",
            stderr=str(exc),
            elapsed_seconds=0.0,
            command=cmd,
        )
