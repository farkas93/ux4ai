#!/usr/bin/env bash
set -euo pipefail

: "${AIPM_DATABASE_URL:?Set AIPM_DATABASE_URL to a PostgreSQL connection URL}"

if [[ $# -ne 1 ]]; then
  printf 'Usage: %s BACKUP_FILE\n' "$0" >&2
  exit 64
fi

backup_file=$1
mkdir -p "$(dirname -- "$backup_file")"
pg_dump --dbname="$AIPM_DATABASE_URL" --format=custom --file="$backup_file"
printf 'Backup written to %s\n' "$backup_file"
