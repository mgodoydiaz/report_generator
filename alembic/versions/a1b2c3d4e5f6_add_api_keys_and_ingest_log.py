"""add api_keys and ingest_log tables

Crea la superficie de datos del workstream W1 (ingesta por API externa):

  - api_keys:   credenciales por organización para ingesta programática.
                El secreto en claro NUNCA se guarda; solo bcrypt(key_hash) +
                prefix visible.
  - ingest_log: auditoría e idempotencia de cada operación de ingesta.
                Constraint único (org_id, idempotency_key).

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e1
Create Date: 2026-07-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('prefix', sa.String(length=12), nullable=False),
        sa.Column('key_hash', sa.String(length=200), nullable=False),
        sa.Column('scopes', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_api_keys_id', 'api_keys', ['id'])
    op.create_index('ix_api_keys_org_id', 'api_keys', ['org_id'])
    op.create_index('ix_api_keys_prefix', 'api_keys', ['prefix'])

    op.create_table(
        'ingest_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('api_key_id', sa.Integer(), nullable=True),
        sa.Column('idempotency_key', sa.String(length=80), nullable=True),
        sa.Column('endpoint', sa.String(length=80), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('rows_ok', sa.Integer(), nullable=True),
        sa.Column('rows_failed', sa.Integer(), nullable=True),
        sa.Column('response_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id']),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('org_id', 'idempotency_key', name='uq_ingest_log_org_idempotency'),
    )
    op.create_index('ix_ingest_log_id', 'ingest_log', ['id'])
    op.create_index('ix_ingest_log_org_id', 'ingest_log', ['org_id'])
    op.create_index('ix_ingest_log_idempotency_key', 'ingest_log', ['idempotency_key'])


def downgrade() -> None:
    op.drop_index('ix_ingest_log_idempotency_key', table_name='ingest_log')
    op.drop_index('ix_ingest_log_org_id', table_name='ingest_log')
    op.drop_index('ix_ingest_log_id', table_name='ingest_log')
    op.drop_table('ingest_log')

    op.drop_index('ix_api_keys_prefix', table_name='api_keys')
    op.drop_index('ix_api_keys_org_id', table_name='api_keys')
    op.drop_index('ix_api_keys_id', table_name='api_keys')
    op.drop_table('api_keys')
