#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo ">>> Rebuilding and redeploying Docker Compose"
docker compose --env-file .env -f docker/docker-compose.yml down
docker compose --env-file .env -f docker/docker-compose.yml up --build -d
docker compose --env-file .env -f docker/docker-compose.yml ps
