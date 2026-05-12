"""Add expense_date to expense

Revision ID: 727638ee871b
Revises: refactor_expense_tracking
Create Date: 2026-05-10 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '727638ee871b'
down_revision = 'refactor_expense_tracking'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('expenses', sa.Column('expense_date', sa.Date(), nullable=True))
    op.execute('UPDATE expenses SET expense_date = CURRENT_DATE WHERE expense_date IS NULL')
    op.alter_column('expenses', 'expense_date', nullable=False)


def downgrade():
    op.drop_column('expenses', 'expense_date')