#!/usr/bin/env bash
set -euo pipefail

: "${ZULU_DATABASE_URL:?ZULU_DATABASE_URL must point at the PostgreSQL database}"
BACKUP_DIR="${BACKUP_DIR:-backups}"
mkdir -p "$BACKUP_DIR"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
outfile="$BACKUP_DIR/zulu-postgres-$timestamp.dump"

pg_dump "$ZULU_DATABASE_URL" --format=custom --no-owner --no-privileges --file="$outfile"
sha256sum "$outfile" > "$outfile.sha256"
echo "$outfile"
