"""Add category and image_url to expenses

Revision ID: add_category_image_url
Revises: 727638ee871b
Create Date: 2026-05-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_category_image_url'
down_revision: Union[str, None] = 'add_avatar_url_to_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('expenses', sa.Column('category', sa.String(length=50), nullable=True))
    op.add_column('expenses', sa.Column('image_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('expenses', 'image_url')
    op.drop_column('expenses', 'category')