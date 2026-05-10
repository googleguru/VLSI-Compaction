#!/usr/bin/env bash
# Run CA-enhanced compaction with the full composite rule policy.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT"

POLICY="${CA_POLICY:-full_composite}"

echo "[ca-run] Running CA-enhanced compaction (policy: $POLICY)..."

python3 -m src.eval.ca_eval \
  --config    "$ROOT/configs/default.yaml" \
  --ca-config "$ROOT/configs/ca_rules.yaml" \
  --benchmarks "$ROOT/configs/benchmarks.yaml" \
  --policy    "$POLICY" \
  --out-dir   "$ROOT/outputs"

echo "[ca-run] Results written to outputs/tables/ca_results.csv"
