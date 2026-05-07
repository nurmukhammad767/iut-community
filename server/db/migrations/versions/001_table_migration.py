"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-06
"""
from alembic import op

# --- Required Alembic headers ---
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Read and execute the SQL file
    file_path = "/app/migrations/versions/001_init.sql"

    with open(file_path, 'r') as f:
        sql_content = f.read()

    op.execute(sql_content)


def downgrade() -> None:
    # Drop in reverse order to handle foreign key constraints
    op.execute("DROP TABLE IF EXISTS club_members CASCADE;")
    op.execute("DROP TABLE IF EXISTS clubs CASCADE;")
    op.execute("DROP TABLE IF EXISTS assignments CASCADE;")
    op.execute("DROP TABLE IF EXISTS course_enrollments CASCADE;")
    op.execute("DROP TABLE IF EXISTS courses CASCADE;")
    op.execute("DROP TABLE IF EXISTS users CASCADE;")
    op.execute("DROP TYPE IF EXISTS user_role;")