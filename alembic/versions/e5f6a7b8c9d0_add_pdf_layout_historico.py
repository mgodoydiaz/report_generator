"""add pdf_layout_historico to indicators

Agrega `pdf_layout_historico` al Indicator. El existente `pdf_layout` se
trata como `pdf_layout_evaluacion` por compatibilidad (no se renombra
para no romper código que ya lo usa).

El frontend ofrece un toggle "Por evaluación / Histórico" en el modal de
generación; el backend lee el campo correspondiente.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'indicators',
        sa.Column('pdf_layout_historico', sa.Text(), nullable=True, server_default='{}')
    )


def downgrade() -> None:
    op.drop_column('indicators', 'pdf_layout_historico')
