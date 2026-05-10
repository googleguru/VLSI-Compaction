"""
Metrics data structures and CSV/table serialization.
"""

import csv
import os
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class CompactionMetrics:
    benchmark:            str
    policy:               str
    area_before:          int      = 0
    area_after:           int      = 0
    area_reduction_pct:   float    = 0.0
    width_before:         int      = 0
    width_after:          int      = 0
    width_reduction_pct:  float    = 0.0
    height_before:        int      = 0
    height_after:         int      = 0
    height_reduction_pct: float    = 0.0
    overlap_count_before: int      = 0
    overlap_count_after:  int      = 0
    spacing_violations:   int      = 0
    runtime_seconds:      float    = 0.0
    iterations:           int      = 0
    xshrf:                float    = 0.0
    yshrf:                float    = 0.0
    ca_epochs:            int      = 0
    ca_converged:         bool     = False
    backend_ok:           bool     = False
    skip_reason:          str      = ""
    notes:                str      = ""

    @classmethod
    def skipped(cls, benchmark: str, policy: str, reason: str) -> "CompactionMetrics":
        return cls(benchmark=benchmark, policy=policy, skip_reason=reason,
                   notes="SKIPPED")


def write_csv(metrics: List[CompactionMetrics], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not metrics:
        logger.warning("No metrics to write to %s", path)
        return
    with open(path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(asdict(metrics[0]).keys()))
        writer.writeheader()
        for m in metrics:
            writer.writerow(asdict(m))
    logger.info("Wrote %d rows to %s", len(metrics), path)


def write_markdown_table(metrics: List[CompactionMetrics], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not metrics:
        return
    cols = [
        "benchmark", "policy",
        "area_reduction_pct", "width_reduction_pct", "height_reduction_pct",
        "overlap_count_after", "runtime_seconds", "iterations", "backend_ok",
    ]
    header = "| " + " | ".join(cols) + " |"
    sep    = "| " + " | ".join(["---"] * len(cols)) + " |"
    rows   = [header, sep]
    for m in metrics:
        d = asdict(m)
        cells = []
        for c in cols:
            v = d.get(c, "")
            if isinstance(v, float):
                cells.append(f"{v:.2f}")
            elif isinstance(v, bool):
                cells.append("yes" if v else "no")
            else:
                cells.append(str(v))
        rows.append("| " + " | ".join(cells) + " |")
    with open(path, "w") as fh:
        fh.write("\n".join(rows) + "\n")
    logger.info("Wrote markdown table to %s", path)
