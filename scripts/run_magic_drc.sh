#!/usr/bin/env bash
# run_magic_drc.sh — batch DRC on all .mag files under outputs/compacted/mag/
#
# Usage:
#   bash scripts/run_magic_drc.sh [CONFIG] [TECH]
#
# Defaults:
#   CONFIG = configs/default.yaml
#   TECH   = scmos
#
# Requires: magic on PATH (otherwise exits 0 with a warning)

set -euo pipefail

CONFIG="${1:-configs/default.yaml}"
TECH="${2:-scmos}"
MAG_DIR="outputs/compacted/mag"
REPORT="outputs/tables/magic_drc_report.txt"

if ! command -v magic &>/dev/null; then
    echo "WARNING: magic not found on PATH — DRC skipped."
    exit 0
fi

mkdir -p "$(dirname "$REPORT")"
echo "Magic DRC batch run — tech: $TECH" > "$REPORT"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$REPORT"
echo "---" >> "$REPORT"

total_violations=0
total_files=0

find "$MAG_DIR" -name "*.mag" | sort | while read -r mag_file; do
    cell_name="$(basename "$mag_file" .mag)"

    # Build a temporary TCL script for batch DRC
    tcl_script="$(mktemp /tmp/magic_drc_XXXXXX.tcl)"
    cat > "$tcl_script" <<TCLEOF
load $mag_file
drc check
set n [drc count]
puts "MAGIC_DRC_FILE $mag_file"
puts "MAGIC_DRC_CELL $cell_name"
puts "MAGIC_DRC_COUNT \$n"
quit
TCLEOF

    # Run Magic in batch mode; capture output
    output="$(magic -dnull -noconsole -T "$TECH" < "$tcl_script" 2>&1 || true)"
    rm -f "$tcl_script"

    count="$(echo "$output" | grep -oP '(?<=MAGIC_DRC_COUNT )\d+' || echo '-1')"

    echo "$cell_name: $count violations" | tee -a "$REPORT"
    total_files=$((total_files + 1))
    if [[ "$count" =~ ^[0-9]+$ ]]; then
        total_violations=$((total_violations + count))
    fi
done

echo "---" >> "$REPORT"
echo "Total violations: $total_violations across $total_files files" | tee -a "$REPORT"
echo "DRC report written to $REPORT"
