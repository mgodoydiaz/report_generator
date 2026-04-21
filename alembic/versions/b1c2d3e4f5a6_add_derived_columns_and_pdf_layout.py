"""add derived_columns and pdf_layout to indicators

Revision ID: b1c2d3e4f5a6
Revises: a778b38fafcb
Create Date: 2026-04-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a778b38fafcb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('indicators', sa.Column('derived_columns', sa.Text(), nullable=True, server_default='[]'))
    op.add_column('indicators', sa.Column('pdf_layout',      sa.Text(), nullable=True, server_default='{}'))


def downgrade() -> None:
    op.drop_column('indicators', 'pdf_layout')
    op.drop_column('indicators', 'derived_columns')
