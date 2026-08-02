#!/usr/bin/env bash
set -e

# Usage: ./db_backup.sh <DATABASE_URL> <BACKUP_FILE_PATH>

DB_URL=$1
BACKUP_PATH=$2

if [ -z "$DB_URL" ] || [ -z "$BACKUP_PATH" ]; then
  echo "Usage: $0 <DATABASE_URL> <BACKUP_FILE_PATH>"
  exit 1
fi

echo "Starting backup of database..."
# Use pg_dump with custom format
pg_dump -Fc --no-acl --no-owner "$DB_URL" -f "$BACKUP_PATH"

echo "Backup complete: $BACKUP_PATH"
