#!/usr/bin/env bash
set -euo pipefail

echo "=== 02: Models & Migrations ==="

# Generate migration SQL from all models
dbwarden make-migrations "create core tables" --database primary

# Show the generated migration file
echo ""
echo "=== Generated Migration ==="
MIGRATION_FILE=$(ls migrations/primary/*.sql 2>/dev/null | head -1)
if [ -n "$MIGRATION_FILE" ]; then
    cat "$MIGRATION_FILE"
fi

# Create a blank manual migration
echo ""
echo "=== Creating manual migration ==="
dbwarden new add_custom_table --database primary

# Show the manual migration template
echo ""
echo "=== Manual migration template ==="
MANUAL_FILE=$(ls migrations/primary/*.sql 2>/dev/null | tail -1)
if [ -n "$MANUAL_FILE" ]; then
    cat "$MANUAL_FILE"
fi

# Generate rollback SQL from the first migration
echo ""
echo "=== Generated rollback SQL ==="
FIRST_FILE=$(ls migrations/primary/*.sql 2>/dev/null | head -1)
if [ -n "$FIRST_FILE" ]; then
    dbwarden make-rollback "$FIRST_FILE"
fi
