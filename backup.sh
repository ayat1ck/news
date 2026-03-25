#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -f ".env" ]]; then
  echo ".env not found. Create it from .env.production.example first."
  exit 1
fi

mkdir -p backups

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
DB_ARCHIVE="backups/postgres_${TIMESTAMP}.sql.gz"
MEDIA_ARCHIVE="backups/media_${TIMESTAMP}.tar.gz"

set -a
source .env
set +a

docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" | gzip > "$DB_ARCHIVE"

tar -czf "$MEDIA_ARCHIVE" backend/media

echo "Created:"
echo "  $DB_ARCHIVE"
echo "  $MEDIA_ARCHIVE"
