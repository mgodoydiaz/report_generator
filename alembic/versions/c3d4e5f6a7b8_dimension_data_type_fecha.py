"""tipo de dato "date" para dimensiones + backfill de data_type

La columna `dimensions.data_type` ya existía (str | int | float) pero era
NULLABLE y sin default: las filas creadas antes de que el router la
expusiera quedaron en NULL. Esta migración

  1. rellena los NULL / vacíos con 'str' (texto, el default histórico),
  2. fija el server_default a 'str',

y deja documentado el nuevo valor admitido 'date' (fecha real), que el
resolver de períodos usa para derivar AÑO y MES desde una columna de
fechas — habilitando los informes semestral y anual en indicadores sin
dimensión "Año" (caso Fluidez Lectora).

El marcado de las dimensiones existentes como 'date' NO se hace acá: es
por organización y depende de los datos, así que vive en el script
`scripts/marcar_dimensiones_fecha.py`.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columnas = {c["name"] for c in inspector.get_columns("dimensions")}

    # Defensivo: en DBs creadas solo por alembic la columna puede no existir.
    if "data_type" not in columnas:
        op.add_column(
            "dimensions",
            sa.Column("data_type", sa.String(length=20),
                      nullable=True, server_default="str"),
        )
    else:
        op.alter_column(
            "dimensions", "data_type",
            existing_type=sa.String(length=20),
            existing_nullable=True,
            server_default="str",
        )

    op.execute(
        "UPDATE dimensions SET data_type = 'str' "
        "WHERE data_type IS NULL OR TRIM(data_type) = ''"
    )


def downgrade() -> None:
    op.alter_column(
        "dimensions", "data_type",
        existing_type=sa.String(length=20),
        existing_nullable=True,
        server_default=None,
    )
    # Las dimensiones marcadas como fecha vuelven al tipo texto.
    op.execute("UPDATE dimensions SET data_type = 'str' WHERE data_type = 'date'")
