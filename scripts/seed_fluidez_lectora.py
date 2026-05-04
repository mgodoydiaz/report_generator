"""Carga inicial de Fluidez Lectora 2026 desde Excel a metric_data.

Crea (idempotente):
- Dimensiones Seguimiento y Calidad lectora (si no existen)
- Métrica "Resultados Fluidez Lectora" con fields Cantidad+Categoria
  y dimensiones (Establecimiento, N Prueba, Curso, Fecha, Seguimiento,
  RUT, Nombre, Calidad lectora)

Carga el archivo Excel del cliente y aplica el mapping_id=32 (FL —
Categoría por Cantidad) sobre la columna Cantidad para poblar Categoria.

Ejecutar (con el archivo accesible en host, copiado a /tmp del container
o vía rebind):
    docker cp "<archivo>" report_generator-backend-1:/tmp/fl.xlsx
    docker exec report_generator-backend-1 python /app/scripts/seed_fluidez_lectora.py /tmp/fl.xlsx
"""
from __future__ import annotations

import json
import sys
from datetime import datetime

sys.path.insert(0, "/app")

import pandas as pd

from backend.database import SessionLocal
from backend.models import Dimension, Metric, MetricData, MetricDimension, Spec, User
from backend.routers.mappings import apply_mapping
from backend.schemas_mapping import MappingConfig


METRIC_NAME = "Resultados Fluidez Lectora"
MAPPING_NAME = "FL — Categoría por Cantidad"


# Mapeo de columna del Excel → nombre canónico en la métrica
COL_MAP = {
    "Establecimiento": "Establecimiento",
    "N Prueba": "N Prueba",
    "Curso": "Curso",
    "Fecha": "Fecha",
    "Seguimiento": "Seguimiento",
    "Rut": "RUT",
    "Nombre": "Nombre",
    "Cantidad": "Cantidad",      # field
    "Categoria": "Categoria",    # field — se recalcula con mapping
    "Calidad lectora": "Calidad lectora",  # dimension
}


def get_or_create_dimension(db, name: str, data_type: str, org_id: int) -> int:
    dim = db.query(Dimension).filter(
        Dimension.name == name, Dimension.org_id == org_id
    ).first()
    if dim:
        return dim.id_dimension
    dim = Dimension(name=name, data_type=data_type, org_id=org_id)
    db.add(dim)
    db.flush()
    print(f"  + dim '{name}' creada (id={dim.id_dimension})")
    return dim.id_dimension


def get_or_create_metric(db, org_id: int, dim_ids: dict) -> Metric:
    m = db.query(Metric).filter(
        Metric.name == METRIC_NAME, Metric.org_id == org_id
    ).first()
    if m:
        return m
    meta = {
        "fields": [
            {"name": "Cantidad", "type": "int"},
            {"name": "Categoria", "type": "str"},
        ]
    }
    m = Metric(
        name=METRIC_NAME,
        data_type="object",
        meta_json=json.dumps(meta, ensure_ascii=False),
        description="Fluidez Lectora — palabras por minuto + categoría aplicada vía mapping",
        org_id=org_id,
    )
    db.add(m)
    db.flush()
    print(f"  + métrica '{METRIC_NAME}' creada (id={m.id_metric})")

    # Asociar dimensiones
    dim_names = ["Establecimiento", "N Prueba", "Curso", "Fecha",
                 "Seguimiento", "RUT", "Nombre", "Calidad lectora"]
    for dn in dim_names:
        link = MetricDimension(id_metric=m.id_metric, id_dimension=dim_ids[dn])
        db.add(link)
    db.flush()
    print(f"  + asociadas {len(dim_names)} dimensiones a metric {m.id_metric}")
    return m


def load_mapping_config(db, org_id: int) -> MappingConfig:
    spec = db.query(Spec).filter(
        Spec.name == MAPPING_NAME, Spec.org_id == org_id, Spec.type == "Mapeo"
    ).first()
    if not spec:
        raise RuntimeError(f"No se encontró el mapeo '{MAPPING_NAME}'. "
                           "Ejecutar primero scripts/seed_mappings.py")
    raw_meta = spec.metadata_
    meta = json.loads(raw_meta) if isinstance(raw_meta, str) else (raw_meta or {})
    cfg_dict = meta.get("mapping_config")
    if not cfg_dict:
        raise RuntimeError(f"Mapeo '{MAPPING_NAME}' sin mapping_config válido")
    return MappingConfig(**cfg_dict)


def load_excel(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="Consolidado")
    # Renombrar columnas al schema canónico
    df = df.rename(columns={src: dst for src, dst in COL_MAP.items() if src in df.columns})
    return df


def main():
    if len(sys.argv) < 2:
        print("Uso: python seed_fluidez_lectora.py <ruta_excel>")
        sys.exit(1)
    excel_path = sys.argv[1]

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == "admin").first()
        org_id = admin.org_id

        # 1. Dimensiones
        print("== Dimensiones ==")
        dim_ids = {
            "Establecimiento": get_or_create_dimension(db, "Establecimiento", "str", org_id),
            "N Prueba": get_or_create_dimension(db, "N Prueba", "str", org_id),  # Ojo: en FL es texto ("Ensayo 1")
            "Curso": get_or_create_dimension(db, "Curso", "str", org_id),
            "Fecha": get_or_create_dimension(db, "Fecha", "str", org_id),
            "Seguimiento": get_or_create_dimension(db, "Seguimiento", "str", org_id),
            "RUT": get_or_create_dimension(db, "RUT", "str", org_id),
            "Nombre": get_or_create_dimension(db, "Nombre", "str", org_id),
            "Calidad lectora": get_or_create_dimension(db, "Calidad lectora", "str", org_id),
        }

        # 2. Métrica
        print("== Métrica ==")
        metric = get_or_create_metric(db, org_id, dim_ids)

        # Si ya tenía datos, los borramos para re-cargar limpio
        existing = db.query(MetricData).filter(
            MetricData.id_metric == metric.id_metric
        ).count()
        if existing:
            print(f"  ! metric {metric.id_metric} ya tenía {existing} rows. Borrando para reload.")
            db.query(MetricData).filter(
                MetricData.id_metric == metric.id_metric
            ).delete(synchronize_session=False)
            db.commit()

        # 3. Mapping
        print("== Mapping ==")
        mapping_cfg = load_mapping_config(db, org_id)
        print(f"  '{MAPPING_NAME}' cargado, kind={mapping_cfg.kind}, "
              f"{len(mapping_cfg.ranges)} tramos")

        # 4. Excel
        print("== Excel ==")
        df = load_excel(excel_path)
        print(f"  shape={df.shape}, cols={list(df.columns)[:8]}…")

        # 5. Aplicar mapping a la columna Cantidad → Categoria
        print("== Recalculando Categoria con mapping ==")
        df["Categoria"] = df["Cantidad"].apply(
            lambda v: apply_mapping(mapping_cfg, v).label
        )
        # Stats
        cat_counts = df["Categoria"].value_counts(dropna=False).to_dict()
        print(f"  distribución Categoria: {cat_counts}")

        # 6. Insertar en metric_data
        print("== Inserción ==")
        rows = []
        for _, r in df.iterrows():
            dims_json = {}
            for dim_name in ["Establecimiento", "N Prueba", "Curso", "Fecha",
                             "Seguimiento", "RUT", "Nombre", "Calidad lectora"]:
                val = r.get(dim_name)
                if pd.notna(val):
                    dims_json[str(dim_ids[dim_name])] = str(val)
            val_obj = {}
            cantidad = r.get("Cantidad")
            categoria = r.get("Categoria")
            if pd.notna(cantidad):
                try:
                    val_obj["Cantidad"] = int(cantidad)
                except (TypeError, ValueError):
                    val_obj["Cantidad"] = cantidad
            if pd.notna(categoria):
                val_obj["Categoria"] = categoria
            rows.append(MetricData(
                id_metric=metric.id_metric,
                value=json.dumps(val_obj, ensure_ascii=False),
                dimensions_json=json.dumps(dims_json, ensure_ascii=False),
                created_at=datetime.utcnow(),
                org_id=org_id,
            ))
        db.bulk_save_objects(rows)
        db.commit()
        print(f"  inserción completada: {len(rows)} rows en metric {metric.id_metric}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
