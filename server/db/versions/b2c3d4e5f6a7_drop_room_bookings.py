"""drop room_bookings table (moved to MongoDB)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-13 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index('idx_room_bookings_student', table_name='room_bookings')
    op.drop_index('idx_room_bookings_day_room', table_name='room_bookings')
    op.drop_table('room_bookings')


def downgrade() -> None:
    """Downgrade schema."""
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
