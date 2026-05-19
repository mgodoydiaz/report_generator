"""Factories — helpers para crear objetos ORM en tests.

Funciones puras: reciben `db` (la session) y kwargs opcionales, devuelven
el objeto ya persistido y refresheado. No usan factory_boy para mantener
deps mínimas — si más adelante crecemos, migrar a factory_boy es trivial.

Convención: cada función toma un counter monotónico para los campos
únicos (slug, email, name) si no se pasan explícitamente. Esto permite
crear varios en el mismo test sin colisiones de UNIQUE.
"""
from __future__ import annotations

import itertools
import json
from typing import Any

from sqlalchemy.orm import Session

# Counters para evitar colisiones UNIQUE entre llamadas dentro del mismo test
_org_counter = itertools.count(1)
_user_counter = itertools.count(1)
_dim_counter = itertools.count(1)
_metric_counter = itertools.count(1)
_indicator_counter = itertools.count(1)


def make_org(db: Session, *, name: str = None, slug: str = None, **kwargs):
    """Crea una Organization."""
    from backend.models import Organization
    n = next(_org_counter)
    o = Organization(
        name=name or f"Org {n}",
        slug=slug or f"org-{n}",
        is_active=kwargs.pop("is_active", True),
        **kwargs,
    )
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


def make_user(
    db: Session,
    org,
    *,
    email: str = None,
    password: str = "test123",
    role: str = "editor",
    is_superadmin: bool = False,
    **kwargs,
):
    """Crea un User vinculado a `org`."""
    from backend.auth import hash_password
    from backend.models import User
    n = next(_user_counter)
    u = User(
        name=kwargs.pop("name", f"User {n}"),
        email=email or f"user{n}@example.com",
        password_hash=hash_password(password),
        org_id=org.id,
        role=role,
        is_active=kwargs.pop("is_active", True),
        is_superadmin=is_superadmin,
        **kwargs,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def make_dimension(
    db: Session,
    org,
    *,
    name: str = None,
    data_type: str = "str",
    **kwargs,
):
    """Crea una Dimension."""
    from backend.models import Dimension
    n = next(_dim_counter)
    d = Dimension(
        name=name or f"Dim {n}",
        data_type=data_type,
        org_id=org.id,
        **kwargs,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def make_metric(
    db: Session,
    org,
    *,
    name: str = None,
    data_type: str = "float",
    fields: list[dict] = None,
    dimensions: list = None,
    **kwargs,
):
    """Crea una Metric, opcionalmente con fields (meta_json) y dimensiones vinculadas."""
    from backend.models import Metric, MetricDimension
    n = next(_metric_counter)
    meta = {"fields": fields} if fields else {}
    m = Metric(
        name=name or f"Metric {n}",
        data_type=data_type,
        meta_json=json.dumps(meta, ensure_ascii=False),
        org_id=org.id,
        **kwargs,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    if dimensions:
        for d in dimensions:
            db.add(MetricDimension(id_metric=m.id_metric, id_dimension=d.id_dimension))
        db.commit()
    return m


def make_metric_data(
    db: Session,
    metric,
    *,
    value: Any = 0.0,
    dimensions_json: dict = None,
    **kwargs,
):
    """Crea una fila de MetricData. value puede ser str/dict (se serializa a JSON)."""
    from backend.models import MetricData
    raw_value = value
    if isinstance(value, dict):
        raw_value = json.dumps(value, ensure_ascii=False)
    elif not isinstance(value, str):
        raw_value = str(value)
    dims = json.dumps(dimensions_json or {}, ensure_ascii=False)
    md = MetricData(
        id_metric=metric.id_metric,
        value=raw_value,
        dimensions_json=dims,
        org_id=metric.org_id,
        **kwargs,
    )
    db.add(md)
    db.commit()
    db.refresh(md)
    return md


def make_indicator(
    db: Session,
    org,
    *,
    name: str = None,
    type_: str = "Evaluación",
    metrics: list = None,
    **kwargs,
):
    """Crea un Indicator. Si `metrics` se pasa, crea los IndicatorMetric links."""
    from backend.models import Indicator, IndicatorMetric
    n = next(_indicator_counter)
    # `type` es palabra reservada en Python; el modelo expone `type` como columna
    ind = Indicator(
        name=name or f"Indicator {n}",
        type=type_,
        org_id=org.id,
        **kwargs,
    )
    db.add(ind)
    db.commit()
    db.refresh(ind)
    if metrics:
        for m in metrics:
            db.add(IndicatorMetric(id_indicator=ind.id_indicator, id_metric=m.id_metric))
        db.commit()
    return ind
