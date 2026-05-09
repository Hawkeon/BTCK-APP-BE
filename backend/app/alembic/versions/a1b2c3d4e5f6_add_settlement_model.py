"""Add Settlement model

Revision ID: a1b2c3d4e5f6
Revises: fe56fa70289e
Create Date: 2026-05-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'fe56fa70289e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'settlement',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('event_id', sa.UUID(), nullable=False),
        sa.Column('from_user_id', sa.UUID(), nullable=False),
        sa.Column('to_user_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('note', sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column('settled_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['event.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_user_id'], ['user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_settlement_event_id'), 'settlement', ['event_id'], unique=False)
    op.create_index(op.f('ix_settlement_from_user_id'), 'settlement', ['from_user_id'], unique=False)
    op.create_index(op.f('ix_settlement_to_user_id'), 'settlement', ['to_user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_settlement_to_user_id'), table_name='settlement')
    op.drop_index(op.f('ix_settlement_from_user_id'), table_name='settlement')
    op.drop_index(op.f('ix_settlement_event_id'), table_name='settlement')
    op.drop_table('settlement')