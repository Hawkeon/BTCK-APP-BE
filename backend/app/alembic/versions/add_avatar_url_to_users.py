"""Add avatar_url to users

Revision ID: add_avatar_url_to_users
Revises: convert_float_to_int_vnd
Create Date: 2026-05-12 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_avatar_url_to_users'
down_revision = 'convert_float_to_int_vnd'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('avatar_url', sa.String(length=500), nullable=True))


def downgrade():
    op.drop_column('users', 'avatar_url')