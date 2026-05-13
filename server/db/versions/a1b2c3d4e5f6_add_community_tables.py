"""add community tables

Revision ID: a1b2c3d4e5f6
Revises: 68a3292668eb
Create Date: 2026-05-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '68a3292668eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'room_bookings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('room_name', sa.String(length=50), nullable=False),
        sa.Column('student_id', sa.UUID(), nullable=False),
        sa.Column('day', sa.String(length=20), nullable=False),
        sa.Column('start_period', sa.Integer(), nullable=False),
        sa.Column('end_period', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False,
                  server_default='active'),
        sa.Column('booked_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'],
                                initially='IMMEDIATE', deferrable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_room_bookings_day_room', 'room_bookings',
                    ['day', 'room_name'], unique=False)
    op.create_index('idx_room_bookings_student', 'room_bookings',
                    ['student_id'], unique=False)

    op.create_table(
        'club_posts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('club_id', sa.UUID(), nullable=False),
        sa.Column('author_id', sa.UUID(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'],
                                initially='IMMEDIATE', deferrable=True),
        sa.ForeignKeyConstraint(['club_id'], ['clubs.id'],
                                initially='IMMEDIATE', deferrable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_club_posts_club_created', 'club_posts',
                    ['club_id', 'created_at'], unique=False)
    # GIN index on tsvector(body) for R6 full-text search
    op.execute(
        "CREATE INDEX idx_club_posts_body_fts ON club_posts "
        "USING GIN (to_tsvector('english', body))"
    )

    op.create_table(
        'room_usage_daily',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('day', sa.String(length=20), nullable=False),
        sa.Column('room_name', sa.String(length=50), nullable=False),
        sa.Column('occupied_periods', sa.Integer(), nullable=False,
                  server_default='0'),
        sa.Column('free_periods', sa.Integer(), nullable=False,
                  server_default='0'),
        sa.Column('computed_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('day', 'room_name', 'computed_at',
                            name='idx_unique_room_usage_daily'),
    )
    op.create_index('idx_room_usage_day', 'room_usage_daily',
                    ['day'], unique=False)

    op.create_table(
        'rate_limit_audit',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('endpoint', sa.String(length=255), nullable=False),
        sa.Column('denied_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                initially='IMMEDIATE', deferrable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_rate_limit_audit_user', 'rate_limit_audit',
                    ['user_id', 'denied_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_rate_limit_audit_user', table_name='rate_limit_audit')
    op.drop_table('rate_limit_audit')

    op.drop_index('idx_room_usage_day', table_name='room_usage_daily')
    op.drop_table('room_usage_daily')

    op.execute("DROP INDEX IF EXISTS idx_club_posts_body_fts")
    op.drop_index('idx_club_posts_club_created', table_name='club_posts')
    op.drop_table('club_posts')

    op.drop_index('idx_room_bookings_student', table_name='room_bookings')
    op.drop_index('idx_room_bookings_day_room', table_name='room_bookings')
    op.drop_table('room_bookings')
