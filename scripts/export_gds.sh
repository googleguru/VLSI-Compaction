#!/usr/bin/env bash
# export_gds.sh — export all .mag files under outputs/compacted/mag/ to GDS2
#
# Usage:
#   bash scripts/export_gds.sh [TECH] [OUT_DIR]
#
# Defaults:
#   TECH    = scmos
#   OUT_DIR = outputs/compacted/gds

set -euo pipefail

TECH="${1:-scmos}"
OUT_DIR="${2:-outputs/compacted/gds}"
MAG_DIR="outputs/compacted/mag"

if ! command -v magic &>/dev/null; then
    echo "WARNING: magic not found on PATH — GDS export skipped."
    exit 0
fi

mkdir -p "$OUT_DIR"

find "$MAG_DIR" -name "*.mag" | sort | while read -r mag_file; do
    cell_name="$(basename "$mag_file" .mag)"
    gds_out="$OUT_DIR/${cell_name}.gds"

    tcl_script="$(mktemp /tmp/magic_gds_XXXXXX.tcl)"
    cat > "$tcl_script" <<TCLEOF
load $mag_file
gds write $gds_out
puts "GDS_WRITTEN $gds_out"
quit
TCLEOF

    output="$(magic -dnull -noconsole -T "$TECH" < "$tcl_script" 2>&1 || true)"
    rm -f "$tcl_script"

    if echo "$output" | grep -q "GDS_WRITTEN"; then
        echo "Exported: $gds_out"
    else
        echo "WARNING: GDS export failed for $mag_file"
    fi
done

echo "GDS export complete → $OUT_DIR"
