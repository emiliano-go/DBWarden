#!/usr/bin/env bash
set -euo pipefail

echo "=== 06: Safety & Impact Analysis ==="

# Run full safety check
echo "--- Safety check on all migrations ---"
dbwarden check --database primary 2>&1

# Check impact of a migration on source code
echo ""
echo "--- Code impact analysis ---"
# Find the latest migration to check
MIG_FILE=$(ls migrations/primary/*.sql 2>/dev/null | head -1)
if [ -n "$MIG_FILE" ]; then
    MIG_NAME=$(basename "$MIG_FILE")
    MIG_NUM=$(echo "$MIG_NAME" | grep -oP '\d{4}')
    echo "Checking impact of migration $MIG_NUM..."
    dbwarden check-impact "$MIG_NUM" --database primary 2>&1 || echo "(no impacts found or requires applied migration)"
fi
