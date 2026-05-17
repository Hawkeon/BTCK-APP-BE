"""Add idempotency_key to settlements

Revision ID: idempotency_settlements
Revises: 25679552766d
Create Date: 2026-05-17
"""
from typing import Sequence, Union

import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'idempotency_settlements'
down_revision: Union[str, None] = '25679552766d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'settlements',
        sa.Column(
            'idempotency_key',
            postgresql.UUID(as_uuid=True),
            nullable=True,
        )
    )
    # Generate UUIDs for existing rows
    op.execute("UPDATE settlements SET idempotency_key = gen_random_uuid() WHERE idempotency_key IS NULL")
    # Make column non-nullable and unique
    op.alter_column('settlements', 'idempotency_key', nullable=False)
    op.create_unique_constraint('uq_settlements_idempotency_key', 'settlements', ['idempotency_key'])
    op.create_index('ix_settlements_idempotency_key', 'settlements', ['idempotency_key'])


def downgrade() -> None:
    op.drop_index('ix_settlements_idempotency_key', table_name='settlements')
    op.drop_constraint('uq_settlements_idempotency_key', 'settlements', type_='unique')
    op.drop_column('settlements', 'idempotency_key')
