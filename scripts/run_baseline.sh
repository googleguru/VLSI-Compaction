#!/usr/bin/env bash
# Run backend-only (no CA) compaction on all available benchmarks.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT"

echo "[baseline] Starting backend-only compaction baseline..."

python3 -m src.eval.baseline_eval \
  --config    "$ROOT/configs/default.yaml" \
  --benchmarks "$ROOT/configs/benchmarks.yaml" \
  --out-dir   "$ROOT/outputs"

echo "[baseline] Results written to outputs/tables/baseline_results.csv"
