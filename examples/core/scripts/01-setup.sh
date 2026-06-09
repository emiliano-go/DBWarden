#!/usr/bin/env bash
set -euo pipefail

echo "=== 01: Project Setup ==="

# Clean any previous state
rm -f app.db
rm -rf migrations .dbwarden

# Initialize DBWarden
dbwarden init

# View the loaded configuration
dbwarden config

echo ""
echo "Setup complete. Files created:"
ls -la dbwarden.py migrations/
