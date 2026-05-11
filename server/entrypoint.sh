#!/bin/bash
set -e

# Check if there are model changes
CHANGES=$(alembic check 2>&1)

if echo "$CHANGES" | grep -q "New upgrade operations detected"; then
    echo "Changes detected, generating migration..."
    alembic revision --autogenerate -m "auto migration"
else
    echo "No changes detected, skipping revision..."
fi

alembic upgrade head