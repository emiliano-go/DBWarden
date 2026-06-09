#!/usr/bin/env bash
set -euo pipefail

echo "=== 04: Offline & CI Workflows ==="

# Ensure models are applied so export has a baseline
dbwarden migrate --database primary 2>/dev/null || true

# Export current model state to JSON
echo "--- Exporting model state ---"
dbwarden export-models --database primary

# Show the exported state file
echo ""
echo "=== Exported Model State ==="
cat .dbwarden/model_state.json 2>/dev/null || echo "(file not found)"

# Generate a migration offline (no database needed)
echo ""
echo "--- Offline migration generation ---"
dbwarden make-migrations "offline schema change" --offline --database primary --verbose 2>&1 || echo "Note: Offline mode requires state to differ from models"
