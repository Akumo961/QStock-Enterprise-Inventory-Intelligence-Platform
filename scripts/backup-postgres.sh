#!/usr/bin/env sh
set -eu

: "${POSTGRES_CONTAINER:=qr-inventory-postgres}"
: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${BACKUP_DIR:=./backups}"
: "${BACKUP_RETENTION_DAYS:=14}"

mkdir -p "$BACKUP_DIR"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_FILE="$BACKUP_DIR/qstock_${TIMESTAMP}.sql.gz"

# pg_dump runs inside the PostgreSQL container so the host does not need
# PostgreSQL client tooling. Credentials remain in the container environment.
docker exec "$POSTGRES_CONTAINER" pg_dump \
  --username="$POSTGRES_USER" \
  --dbname="$POSTGRES_DB" \
  --no-owner \
  --no-privileges \
  | gzip > "$BACKUP_FILE"

# Remove backups older than the configured retention window.
find "$BACKUP_DIR" -type f -name 'qstock_*.sql.gz' -mtime "+$BACKUP_RETENTION_DAYS" -delete

printf 'Created PostgreSQL backup: %s\n' "$BACKUP_FILE"
