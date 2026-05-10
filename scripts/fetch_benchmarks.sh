#!/usr/bin/env bash
# Fetch publicly available benchmark collateral where possible.
# IPSD, ISCAS, and ASAP7 require separate license steps (documented below).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BENCH="$ROOT/data/benchmarks"

mkdir -p "$BENCH"/{ipsd,iscas,asap7}

echo "[fetch] Checking benchmark availability..."

# ── IPSD ─────────────────────────────────────────────────────────────────────
# IPSD layout-ready CIF files are not publicly distributed via automated
# download. Obtain from the original IPSD benchmark suite and place CIF files
# under data/benchmarks/ipsd/.
if ls "$BENCH/ipsd/"*.cif 1>/dev/null 2>&1; then
  echo "[fetch] IPSD CIF files found: $(ls "$BENCH/ipsd/"*.cif | wc -l) file(s)"
else
  echo "[fetch] SKIP ipsd: No CIF files in $BENCH/ipsd/"
  echo "        Provide layout-ready .cif files to enable IPSD benchmarks."
fi

# ── ISCAS-85 ─────────────────────────────────────────────────────────────────
# ISCAS-85 benchmarks are distributed as gate-level netlists, not layouts.
# A full synthesis + place-and-route flow is required to generate CIF.
# This script checks for pre-converted CIF outputs only.
if ls "$BENCH/iscas/"*.cif 1>/dev/null 2>&1; then
  echo "[fetch] ISCAS CIF files found: $(ls "$BENCH/iscas/"*.cif | wc -l) file(s)"
else
  echo "[fetch] SKIP iscas: No converted CIF files in $BENCH/iscas/"
  echo "        Run a P&R flow and place output CIF under data/benchmarks/iscas/."
fi

# ── ASAP7 ────────────────────────────────────────────────────────────────────
ASAP7_CFG="$ROOT/configs/asap7.yaml"
PDK_ROOT=$(python3 -c "import yaml; c=yaml.safe_load(open('$ASAP7_CFG')); print(c['asap7']['pdk_root'] or '')" 2>/dev/null || echo "")
if [ -n "$PDK_ROOT" ] && [ -d "$PDK_ROOT" ]; then
  echo "[fetch] ASAP7 PDK found at $PDK_ROOT"
  bash "$ROOT/scripts/convert_inputs.sh" --asap7
else
  echo "[fetch] SKIP asap7: pdk_root not configured in configs/asap7.yaml"
fi

echo "[fetch] Done. Demo benchmarks are always available at data/demo/."
