"""Refactor database schema for expense tracking

- Rename Event.owner_id to created_by_id
- Remove EventMember.id (use composite PK: event_id, user_id)
- Remove Expense.expense_date, category, split_type
- Add Expense.created_by_id, remove ExpenseSplit.id (composite PK)
- Remove ExpenseSplit.is_excluded
- Add User.qr_code_url
- Rename Settlement.settled_at to created_at

Revision ID: refactor_expense_tracking
Revises:
Create Date: 2026-05-10
"""
from typing import Sequence, Union

import uuid
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'refactor_expense_tracking'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop stale singular tables created by initial_data.py / SQLModel create_all
    op.execute("DROP TABLE IF EXISTS expense_splits CASCADE")
    op.execute("DROP TABLE IF EXISTS expenses CASCADE")
    op.execute("DROP TABLE IF EXISTS settlements CASCADE")
    op.execute("DROP TABLE IF EXISTS event_members CASCADE")
    op.execute("DROP TABLE IF EXISTS events CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")

    # Drop stale singular tables (created by SQLModel default naming before migration)
    op.execute("DROP TABLE IF EXISTS expensesplit CASCADE")
    op.execute("DROP TABLE IF EXISTS expense CASCADE")
    op.execute("DROP TABLE IF EXISTS eventmember CASCADE")
    op.execute("DROP TABLE IF EXISTS event CASCADE")
    op.execute('DROP TABLE IF EXISTS "user" CASCADE')

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, default=False),
        sa.Column('qr_code_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create events table
    op.create_table(
        'events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create event_members table (composite PK)
    op.create_table(
        'event_members',
        sa.Column('event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('events.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create expenses table
    op.create_table(
        'expenses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('payer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create expense_splits table (composite PK)
    op.create_table(
        'expense_splits',
        sa.Column('expense_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('expenses.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('amount_owed', sa.Float(), nullable=False),
    )

    # Create settlements table
    op.create_table(
        'settlements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('from_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('to_user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('note', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create invite_codes table
    op.create_table(
        'invite_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False, unique=True),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('max_uses', sa.Integer(), nullable=True),
        sa.Column('use_count', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_events_created_by_id', 'events', ['created_by_id'])
    op.create_index('ix_invite_codes_code', 'invite_codes', ['code'])


def downgrade() -> None:
    # This is a development migration - no downgrade needed
    pass