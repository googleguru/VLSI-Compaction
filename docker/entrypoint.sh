#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=/app

case "${1:-help}" in
  help)
    echo "VLSI CA Compaction Framework"
    echo ""
    echo "Commands:"
    echo "  baseline     Run backend-only baseline compaction"
    echo "  ca-run       Run CA-enhanced compaction"
    echo "  ablation     Run all ablation configurations"
    echo "  report       Generate figures and update README"
    echo "  full-run     Run baseline + ablation + report"
    echo "  shell        Drop into bash"
    ;;
  baseline)
    bash /app/scripts/run_baseline.sh
    ;;
  ca-run)
    bash /app/scripts/run_ca_compaction.sh
    ;;
  ablation)
    bash /app/scripts/run_ablation.sh
    ;;
  report)
    bash /app/scripts/make_report.sh
    ;;
  full-run)
    bash /app/scripts/run_baseline.sh
    bash /app/scripts/run_ca_compaction.sh
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
