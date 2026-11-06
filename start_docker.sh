#!/usr/bin/env bash
# Start the stack. Stop it with: docker compose down
set -euo pipefail

case "${1:-}" in
    cpu) docker compose up -d ;;
    gpu) docker compose -f docker-compose.yaml -f docker-compose.gpu.yaml up -d ;;
    *)   echo "usage: ${0##*/} {cpu|gpu}" >&2; exit 1 ;;
esac
