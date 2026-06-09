#!/usr/bin/env bash
set -euo pipefail

echo "=== 07: Seeds ==="

# Ensure migrations are applied
mkdir -p seeds
dbwarden migrate --database primary 2>/dev/null || true

# Create a SQL seed file
echo "--- Creating SQL seed ---"
dbwarden seed create "initial admin users" --database primary

# Populate the seed file with content
SEED_FILE=$(ls seeds/V*.sql 2>/dev/null | head -1)
if [ -n "$SEED_FILE" ]; then
    cat > "$SEED_FILE" << 'SEEDEOF'
-- Seed: initial admin users
-- Applied once and tracked in _dbwarden_seeds

INSERT INTO users (email, username, full_name, is_active, created_at)
VALUES ('admin@example.com', 'admin', 'Admin User', 1, CURRENT_TIMESTAMP);

INSERT INTO users (email, username, full_name, is_active, created_at)
VALUES ('moderator@example.com', 'moderator', 'Moderator User', 1, CURRENT_TIMESTAMP);
SEEDEOF
    echo "Seed file written: $SEED_FILE"
fi

# Apply seeds
echo ""
echo "--- Applying seeds ---"
dbwarden seed apply --database primary

# List applied seeds
echo ""
echo "--- Applied seeds ---"
dbwarden seed list --database primary

# Create another seed
echo ""
echo "--- Creating second seed ---"
dbwarden seed create "demo products" --database primary

SEED_FILE2=$(ls seeds/V*.sql 2>/dev/null | tail -1)
if [ -n "$SEED_FILE2" ] && [ "$SEED_FILE2" != "$SEED_FILE" ]; then
    cat > "$SEED_FILE2" << 'SEEDEOF'
-- Seed: demo products

INSERT INTO products (name, price, description, in_stock, created_at)
VALUES ('Widget', 9.99, 'A standard widget', 1, CURRENT_TIMESTAMP);

INSERT INTO products (name, price, description, in_stock, created_at)
VALUES ('Gadget', 24.99, 'A fancy gadget', 1, CURRENT_TIMESTAMP);

INSERT INTO products (name, price, description, in_stock, created_at)
VALUES ('Doohickey', 4.99, 'A small doohickey', 1, CURRENT_TIMESTAMP);
SEEDEOF
    echo "Seed file written: $SEED_FILE2"
fi

# Apply the second seed
dbwarden seed apply --database primary

# List all seeds
echo ""
echo "--- All seeds after applying second ---"
dbwarden seed list --database primary

# Rollback the last seed
echo ""
echo "--- Rolling back last seed ---"
dbwarden seed rollback --database primary --count 1

# List after rollback
echo ""
echo "--- Seeds after rollback ---"
dbwarden seed list --database primary
