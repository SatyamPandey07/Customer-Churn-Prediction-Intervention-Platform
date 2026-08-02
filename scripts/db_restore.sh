#!/usr/bin/env bash
set -e

# Usage: ./db_restore.sh <DATABASE_URL> <BACKUP_FILE_PATH>

DB_URL=$1
BACKUP_PATH=$2

if [ -z "$DB_URL" ] || [ -z "$BACKUP_PATH" ]; then
  echo "Usage: $0 <DATABASE_URL> <BACKUP_FILE_PATH>"
  exit 1
fi

echo "Starting restore of database from $BACKUP_PATH..."
# pg_restore using clean option to drop objects before recreating them
# Ignore errors during restore (e.g., if a table to drop doesn't exist)
pg_restore -c -O -d "$DB_URL" "$BACKUP_PATH" || true

echo "Restore complete."
