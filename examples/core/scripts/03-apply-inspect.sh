#!/usr/bin/env bash
set -euo pipefail

echo "=== 03: Apply & Inspect ==="

# Apply all pending migrations
echo "--- Applying migrations ---"
dbwarden migrate --database primary

# Check status
echo ""
echo "--- Migration Status ---"
dbwarden status --database primary

# View history
echo ""
echo "--- Migration History ---"
dbwarden history --database primary

# Rollback the last migration
echo ""
echo "--- Rolling back 1 migration ---"
dbwarden rollback --database primary --count 1

# Confirm it was rolled back
echo ""
echo "--- Status after rollback ---"
dbwarden status --database primary

# Re-apply
echo ""
echo "--- Re-applying ---"
dbwarden migrate --database primary

# Rollback to a specific version
echo ""
echo "--- Downgrade to version 0000 (all rolled back) ---"
dbwarden downgrade --to 0000 --database primary
dbwarden status --database primary

# Re-apply all
echo ""
echo "--- Final apply ---"
dbwarden migrate --database primary
dbwarden status --database primary

# Validate schema
echo ""
echo "--- Schema validation (check) ---"
dbwarden check --database primary

# Check DB connectivity
echo ""
echo "--- Database connectivity (check-db) ---"
dbwarden check-db --database primary
