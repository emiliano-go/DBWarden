#!/usr/bin/env bash
set -euo pipefail

echo "=== 05: Schema Inspection ==="

# Ensure migrations are applied first
dbwarden migrate --database primary 2>/dev/null || true

# Diff models vs database
echo "--- Diff: models vs database ---"
dbwarden diff --database primary 2>&1 || echo "(no differences expected)"

# Snapshot a specific table
echo ""
echo "--- DDL Snapshot: users table ---"
dbwarden snapshot users --database primary 2>&1 || echo "Note: snapshot requires a live PostgreSQL database"
