import os
from alembic import op

def upgrade() -> None:
    # The path inside the container[cite: 1]
    file_path = "/app/db/migration/001_init.sql"[cite: 1]
    
    with open(file_path, 'r') as f:
        sql_content = f.read()
    
    # Executes the schema: user_role ENUM, users, courses, etc.[cite: 1]
    op.execute(sql_content) 

def downgrade() -> None:
    # Drop in reverse order to handle foreign key constraints[cite: 1]
    op.execute("DROP TABLE IF EXISTS club_members CASCADE;")[cite: 1]
    op.execute("DROP TABLE IF EXISTS clubs CASCADE;")[cite: 1]
    op.execute("DROP TABLE IF EXISTS assignments CASCADE;")[cite: 1]
    op.execute("DROP TABLE IF EXISTS course_enrollments CASCADE;")[cite: 1]
    op.execute("DROP TABLE IF EXISTS courses CASCADE;")[cite: 1]
    op.execute("DROP TABLE IF EXISTS users CASCADE;")[cite: 1]
    op.execute("DROP TYPE IF EXISTS user_role;")[cite: 1]