#!/usr/bin/env bash
# Convert benchmark inputs to CIF format required by the compaction backend.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT"

ASAP7_MODE=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --asap7) ASAP7_MODE=true; shift ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

echo "[convert] Running geometry normalization..."
python3 -m src.io.geometry_normalizer \
  --ipsd-dir "$ROOT/data/benchmarks/ipsd" \
  --iscas-dir "$ROOT/data/benchmarks/iscas" \
  --out-dir   "$ROOT/data/benchmarks"

if $ASAP7_MODE; then
  echo "[convert] Running ASAP7 CIF extraction..."
  python3 -m src.io.ipsd_adapter --mode asap7 \
    --config "$ROOT/configs/asap7.yaml" \
    --out-dir "$ROOT/data/benchmarks/asap7"
fi

echo "[convert] Done."
