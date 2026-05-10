#!/usr/bin/env bash
# Run all ablation configurations and collect comparison metrics.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT"

echo "[ablation] Running ablation study..."

python3 -m src.eval.ablation_runner \
  --config     "$ROOT/configs/default.yaml" \
  --ca-config  "$ROOT/configs/ca_rules.yaml" \
  --benchmarks "$ROOT/configs/benchmarks.yaml" \
  --out-dir    "$ROOT/outputs"

echo "[ablation] Results written to outputs/tables/ablation_results.csv"
