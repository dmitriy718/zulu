#!/usr/bin/env bash
set -euo pipefail

: "${ZULU_DATABASE_URL:?ZULU_DATABASE_URL must point at the restore target}"
: "${BACKUP_FILE:?BACKUP_FILE must point at a pg_dump custom-format file}"

if [[ -f "$BACKUP_FILE.sha256" ]]; then
  sha256sum --check "$BACKUP_FILE.sha256"
fi

pg_restore "$BACKUP_FILE" \
  --dbname="$ZULU_DATABASE_URL" \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges
