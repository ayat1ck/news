#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -f ".env" ]]; then
  echo ".env not found. Create it from .env.production.example first."
  exit 1
fi

mkdir -p backend/media backups

docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
