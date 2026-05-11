#!/usr/bin/env bash
# Build the Docker image for the Rule-110 compaction framework.
# Usage: bash scripts/build_docker.sh [--no-cache]

set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

TAG="vlsi-rule110-compaction:latest"
NO_CACHE="${1:-}"

echo "=== Building Docker image: $TAG ==="
docker compose -f docker/docker-compose.yml build $NO_CACHE

echo "=== Build complete: $TAG ==="
echo "Run the full pipeline:"
echo "  docker compose -f docker/docker-compose.yml run --rm compaction full-run"
echo "Run synthesis only:"
echo "  docker compose -f docker/docker-compose.yml run --rm compaction synth"
echo "Run ablation study:"
echo "  docker compose -f docker/docker-compose.yml run --rm compaction ablation"
