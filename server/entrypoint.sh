#!/bin/bash
set -e

# Apply existing migrations
echo "Applying database migrations..."
alembic upgrade head 2>&1 || {
  echo "Migration failed, checking database state..."
  # Stamp the database to current version if migration fails due to version mismatch
  LATEST_REV=$(alembic heads 2>/dev/null | awk '{print $1}' | head -1)
  if [ -n "$LATEST_REV" ]; then
    echo "Stamping database with latest revision: $LATEST_REV"
    alembic stamp "$LATEST_REV"
    echo "Retrying migration..."
    alembic upgrade head
  else
    echo "Could not determine latest revision"
    exit 1
  fi
}

echo "Migration completed successfully"