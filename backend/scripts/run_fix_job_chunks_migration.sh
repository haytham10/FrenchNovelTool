#!/usr/bin/env bash
# Wrapper to run the fix_job_chunks_migration.sql against the DATABASE_URL
# Usage: ./run_fix_job_chunks_migration.sh
# Ensure DATABASE_URL is exported or set in environment before running.

set -euo pipefail

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL environment variable is not set. Export it and retry."
  exit 1
fi

SCRIPT_DIR="$(dirname "$0")"
psql "$DATABASE_URL" -f "$SCRIPT_DIR/fix_job_chunks_migration.sql"

echo "Done. If indexes were dropped, re-run your migration: flask db upgrade (or redeploy)."
