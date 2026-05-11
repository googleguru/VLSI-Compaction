#!/usr/bin/env bash
# Run Rule-110 guided compaction on all available benchmarks.
# Usage: bash scripts/run_compaction.sh [policy] [--config configs/default.yaml]
#   policy: r110_alternating_adaptive (default) | r110_alternating | r110_row_only | ...

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

POLICY="${1:-r110_alternating_adaptive}"
CONFIG="${2:-configs/default.yaml}"
R110_CONFIG="configs/rule110.yaml"
BENCHMARKS="configs/benchmarks.yaml"
OUT_DIR="outputs"

echo "=== Rule-110 compaction run ==="
echo "    policy=$POLICY config=$CONFIG"

mkdir -p "$OUT_DIR/compacted" "$OUT_DIR/tables" "$OUT_DIR/logs"

python3 -m src.eval.rule110_eval \
    --config      "$CONFIG" \
    --rule110-config "$R110_CONFIG" \
    --benchmarks  "$BENCHMARKS" \
    --policy      "$POLICY" \
    --out-dir     "$OUT_DIR" \
    2>&1 | tee "$OUT_DIR/logs/compaction_${POLICY}.log"

echo "=== Compaction complete. Results in $OUT_DIR/tables/ ==="
