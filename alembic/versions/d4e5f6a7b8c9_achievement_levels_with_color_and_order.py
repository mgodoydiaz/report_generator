"""achievement_levels with color and order

Revision ID: d4e5f6a7b8c9
Revises: ca5eff95edd4
Create Date: 2026-04-21 00:00:00.000000

Migra achievement_levels de formato dict {name: order} o lista de strings
al nuevo formato [{name, color, order}].
"""
from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'ca5eff95edd4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_COLORS = {
    "Crítico":       "#dc2626",
    "Critico":       "#dc2626",
    "Alto Riesgo":   "#ea580c",
    "Cierto Riesgo": "#eab308",
    "Bajo Riesgo":   "#16a34a",
}


def _to_new_format(levels):
    """Convierte cualquier formato previo a [{name, color, order}]. Retorna None si no aplica."""
    if not levels:
        return None
    # Ya está en formato nuevo
    if isinstance(levels, list) and levels and isinstance(levels[0], dict) and 'name' in levels[0]:
        return None
    new = []
    if isinstance(levels, dict):
        for name, order in sorted(levels.items(), key=lambda x: x[1]):
            new.append({"name": name, "order": int(order), "color": DEFAULT_COLORS.get(name, "#94a3b8")})
    elif isinstance(levels, list) and all(isinstance(l, str) for l in levels):
        for i, name in enumerate(levels):
            new.append({"name": name, "order": i + 1, "color": DEFAULT_COLORS.get(name, "#94a3b8")})
    else:
        return None
    return new


def _to_legacy_format(levels):
    """Revierte [{name, color, order}] a {name: order}. Retorna None si no aplica."""
    if not levels:
        return None
    if not (isinstance(levels, list) and levels and isinstance(levels[0], dict) and 'name' in levels[0]):
        return None
    return {l['name']: l.get('order', i + 1) for i, l in enumerate(levels)}


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id_indicator, achievement_levels FROM indicators")).fetchall()
    for id_indicator, raw in rows:
        try:
            levels = json.loads(raw) if raw else []
        except Exception:
            continue
        new_levels = _to_new_format(levels)
        if new_levels is None:
            continue
        bind.execute(
            sa.text("UPDATE indicators SET achievement_levels = :val WHERE id_indicator = :id"),
            {"val": json.dumps(new_levels, ensure_ascii=False), "id": id_indicator},
        )


def downgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id_indicator, achievement_levels FROM indicators")).fetchall()
    for id_indicator, raw in rows:
        try:
            levels = json.loads(raw) if raw else []
        except Exception:
            continue
        legacy = _to_legacy_format(levels)
        if legacy is None:
            continue
        bind.execute(
            sa.text("UPDATE indicators SET achievement_levels = :val WHERE id_indicator = :id"),
            {"val": json.dumps(legacy, ensure_ascii=False), "id": id_indicator},
        )
