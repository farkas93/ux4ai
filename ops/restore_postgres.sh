#!/usr/bin/env bash
set -euo pipefail

: "${AIPM_DATABASE_URL:?Set AIPM_DATABASE_URL to a PostgreSQL connection URL}"

if [[ $# -ne 1 ]]; then
  printf 'Usage: %s BACKUP_FILE\n' "$0" >&2
  exit 64
fi

if [[ "${CONFIRM_RESTORE:-}" != "YES" ]]; then
  printf 'Refusing destructive restore. Set CONFIRM_RESTORE=YES explicitly.\n' >&2
  exit 1
fi

backup_file=$1
if [[ ! -f "$backup_file" ]]; then
  printf 'Backup file does not exist: %s\n' "$backup_file" >&2
  exit 66
fi

pg_restore --dbname="$AIPM_DATABASE_URL" --clean --if-exists --no-owner "$backup_file"
printf 'Restore completed from %s\n' "$backup_file"
