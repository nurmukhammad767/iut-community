#!/bin/bash
set -e
# Generate migration if models changed
alembic revision --autogenerate -m "auto migration"
# Apply migrations
alembic upgrade head