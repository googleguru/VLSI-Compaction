#!/usr/bin/env bash
# Synthesize Verilog benchmarks with Yosys.
# Produces gate-level netlists in outputs/netlists/.
# Usage: bash scripts/run_synth.sh [--config configs/default.yaml]

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

CONFIG="${1:-configs/default.yaml}"
echo "=== Synthesis run: config=$CONFIG ==="

# Check Yosys availability; warn but don't fail (pipeline continues with
# synthetic geometry if Yosys is absent)
if ! command -v yosys &>/dev/null; then
    echo "WARNING: yosys not found. Synthesis will be skipped; synthetic" \
         "cell geometry templates will be used instead."
fi

python3 - <<'EOF'
import sys, yaml, logging, os
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

with open("configs/default.yaml") as fh:
    cfg = yaml.safe_load(fh)

synth_cfg = cfg.get("synth", {})
out_dir   = synth_cfg.get("out_dir", "outputs/netlists")
liberty   = synth_cfg.get("liberty_path")
top       = synth_cfg.get("top_module")

from src.synth.yosys_runner import YosysRunner
runner = YosysRunner(
    yosys_bin=synth_cfg.get("yosys_bin", "yosys"),
    timeout=synth_cfg.get("timeout", 300),
)

verilog_files = [
    "data/demo/iscas/c17.v",
    "data/demo/iscas/s27.v",
    "data/demo/iscas/c432.v",
]

for vf in verilog_files:
    if not os.path.isfile(vf):
        print(f"SKIP: {vf} not found")
        continue
    print(f"Synthesizing {vf} ...")
    stats = runner.synthesize(vf, out_dir, top_module=top, liberty_path=liberty)
    if stats.success:
        print(f"  OK: {stats.num_cells} cells, area={stats.chip_area:.1f}")
    else:
        print(f"  SKIP: {stats.error_message}")

print("Synthesis stage complete.")
EOF
