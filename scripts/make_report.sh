#!/usr/bin/env bash
# Generate all figures, tables, and update README.md.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$ROOT"

echo "[report] Generating publication-ready figures..."
python3 -m src.viz.figure_exporter \
  --out-dir "$ROOT/outputs" \
  --config  "$ROOT/configs/default.yaml"

echo "[report] Generating markdown summary..."
python3 -m src.report.summary_generator \
  --out-dir "$ROOT/outputs"

echo "[report] Updating README.md..."
python3 -m src.report.readme_updater \
  --root "$ROOT"

echo "[report] Done. See outputs/reports/ and README.md."
