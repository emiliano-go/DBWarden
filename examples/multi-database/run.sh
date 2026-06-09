#!/usr/bin/env bash
set -euo pipefail

echo "=== Multi-Database Example ==="
echo "This requires Docker for PostgreSQL and ClickHouse."
echo ""

# Start databases
echo "Starting PostgreSQL and ClickHouse..."
docker compose up -d
echo "Waiting for databases to be ready..."
sleep 5

# Initialize
echo ""
echo "--- Initializing ---"
dbwarden init 2>&1

# Generate migrations for both databases
echo ""
echo "--- Generating migrations ---"
dbwarden make-migrations "create user table" --database primary 2>&1
dbwarden make-migrations "create page view table" --database analytics 2>&1

# Check status
echo ""
echo "--- Status (all) ---"
dbwarden status --all 2>&1

# Apply
echo ""
echo "--- Applying migrations ---"
dbwarden migrate --all 2>&1

echo ""
echo "=== Done ==="
echo "Databases are running. Stop them with: docker compose down"
