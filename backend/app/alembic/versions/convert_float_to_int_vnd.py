"""Convert float to int for VND

Revision ID: convert_float_to_int_vnd
Revises: 727638ee871b
Create Date: 2026-05-11 07:15:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'convert_float_to_int_vnd'
down_revision = '727638ee871b'
branch_labels = None
depends_on = None


def upgrade():
    # Convert expense.amount from float to int
    op.execute("ALTER TABLE expenses ALTER COLUMN amount TYPE integer USING amount::integer")

    # Convert expensesplit.amount_owed from float to int
    op.execute("ALTER TABLE expense_splits ALTER COLUMN amount_owed TYPE integer USING amount_owed::integer")

    # Convert settlement.amount from float to int
    op.execute("ALTER TABLE settlements ALTER COLUMN amount TYPE integer USING amount::integer")


def downgrade():
    # Revert to float
    op.execute("ALTER TABLE expenses ALTER COLUMN amount TYPE double precision USING amount::double precision")
    op.execute("ALTER TABLE expense_splits ALTER COLUMN amount_owed TYPE double precision USING amount_owed::double precision")
    op.execute("ALTER TABLE settlements ALTER COLUMN amount TYPE double precision USING amount::double precision")