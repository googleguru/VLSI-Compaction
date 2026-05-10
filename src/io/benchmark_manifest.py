"""
Benchmark manifest loader and availability checker.
"""

import os
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional
import yaml

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkEntry:
    name: str
    path: str
    bench_type: str
    description: str
    available: bool
    skip_reason: Optional[str]

    def is_ready(self) -> bool:
        if not self.available:
            return False
        return os.path.isfile(self.path)


class BenchmarkManifest:
    def __init__(self, config_path: str):
        with open(config_path) as fh:
            raw = yaml.safe_load(fh)
        self._entries: Dict[str, BenchmarkEntry] = {}
        for name, spec in raw.get("benchmarks", {}).items():
            available = spec.get("available", False)
            path = spec.get("path", "")
            # Re-check filesystem regardless of config flag
            file_exists = os.path.isfile(path)
            entry = BenchmarkEntry(
                name=name,
                path=path,
                bench_type=spec.get("type", "unknown"),
                description=spec.get("description", ""),
                available=available and file_exists,
                skip_reason=spec.get("skip_reason"),
            )
            self._entries[name] = entry

    def ready(self) -> List[BenchmarkEntry]:
        return [e for e in self._entries.values() if e.is_ready()]

    def skipped(self) -> List[BenchmarkEntry]:
        return [e for e in self._entries.values() if not e.is_ready()]

    def get(self, name: str) -> Optional[BenchmarkEntry]:
        return self._entries.get(name)

    def log_summary(self) -> None:
        ready = self.ready()
        skipped = self.skipped()
        logger.info("Benchmark manifest: %d ready, %d skipped", len(ready), len(skipped))
        for e in ready:
            logger.info("  [READY]   %s  %s", e.name, e.path)
        for e in skipped:
            reason = (e.skip_reason or "file not found").strip().replace("\n", " ")[:80]
            logger.info("  [SKIP]    %s  reason: %s", e.name, reason)
