"""add audit columns to metric_data

Agrega campos de auditoría a `metric_data` para registrar quién, con qué
proceso, y desde qué IP se cargó cada dato:

  - created_by_user_id: FK a users.id (NULL si fue carga legacy o cron sin usuario)
  - created_via:        'pipeline' | 'pipeline_cron' | 'import_csv' | 'manual_single' | 'api_direct'
  - created_from_ip:    IP de origen (NULL si no se capturó)

Filas existentes (~19k local, ~18k prod) quedan con los 3 campos en NULL
y la UI las muestra como "(legacy)".

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'metric_data',
        sa.Column(
            'created_by_user_id',
            sa.Integer(),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
    )
    op.add_column(
        'metric_data',
        sa.Column('created_via', sa.String(length=20), nullable=True),
    )
    op.add_column(
        'metric_data',
        sa.Column('created_from_ip', sa.String(length=45), nullable=True),
    )
    op.create_index(
        'ix_metric_data_created_by_user_id',
        'metric_data',
        ['created_by_user_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_metric_data_created_by_user_id', table_name='metric_data')
    op.drop_column('metric_data', 'created_from_ip')
    op.drop_column('metric_data', 'created_via')
    op.drop_column('metric_data', 'created_by_user_id')
