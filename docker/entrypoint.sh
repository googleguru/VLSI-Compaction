#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=/app

case "${1:-help}" in
  help)
    echo "Rule-110 CA Guided Layout Compaction Framework"
    echo "(Yosys + Cell-Based-Layout-Compaction + Rule 110 CA planner)"
    echo ""
    echo "Commands:"
    echo "  synth        Synthesize Verilog benchmarks with Yosys"
    echo "  compact      Run Rule-110 guided compaction (POLICY env var)"
    echo "  baseline     Run backend-only baseline compaction"
    echo "  ablation     Run all Rule-110 + composite ablation policies"
    echo "  figures      Export publication-ready figures"
    echo "  report       Generate figures and update README"
    echo "  full-run     synth → compact → ablation → report"
    echo "  shell        Drop into bash"
    echo ""
    echo "Environment variables:"
    echo "  POLICY            CA policy name (default: r110_alternating_adaptive)"
    echo "  RULE110_CONFIG    path to rule110.yaml"
    echo "  CA_CONFIG         path to ca_rules.yaml (legacy composite)"
    ;;
  synth)
    bash /app/scripts/run_synth.sh /app/configs/default.yaml
    ;;
  compact)
    bash /app/scripts/run_compaction.sh "${POLICY:-r110_alternating_adaptive}"
    ;;
  baseline)
    bash /app/scripts/run_baseline.sh
    ;;
  ablation)
    bash /app/scripts/run_ablation.sh
    ;;
  figures)
    python3 -m src.viz.figure_exporter \
        --config  /app/configs/default.yaml \
        --out-dir /app/outputs
    ;;
  report)
    bash /app/scripts/make_report.sh
    ;;
  full-run)
    bash /app/scripts/run_synth.sh
    bash /app/scripts/run_compaction.sh "${POLICY:-r110_alternating_adaptive}"
    bash /app/scripts/run_ablation.sh
    bash /app/scripts/make_report.sh
    ;;
  shell)
    exec bash
    ;;
  *)
    echo "Unknown command: $1" >&2
    exit 1
    ;;
esac
