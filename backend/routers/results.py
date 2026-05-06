import json
import traceback
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import get_current_user
from backend.models import (
    User, Indicator, IndicatorMetric,
    Metric, MetricDimension, MetricData, Dimension,
)

router = APIRouter(prefix="/api/results", tags=["results"])


def _parse_json_field(value, default):
    if isinstance(value, str) and value:
        try:
            return json.loads(value.replace("'", '"'))
        except Exception:
            return default
    if value is None:
        return default
    if isinstance(value, type(default)):
        return value
    return default


@router.get("/indicator/{indicator_id}/data")
async def get_indicator_data(
    indicator_id: int,
    filters: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Devuelve todos los datos de las métricas asociadas a un indicador,
    opcionalmente filtrados por dimensiones.

    filters: JSON string con {id_dimension: valor}, e.g. '{"1": "2025", "3": "Lenguaje"}'
    """
    try:
        # 1. Verify indicator belongs to org and get metric relations
        indicator = db.query(Indicator).filter(
            Indicator.id_indicator == indicator_id,
            Indicator.org_id == user.org_id,
        ).first()
        if not indicator:
            return {"metrics": [], "data": {}, "dimensions": {}}

        metric_links = db.query(IndicatorMetric).filter(
            IndicatorMetric.id_indicator == indicator_id
        ).all()
        metric_ids = [lnk.id_metric for lnk in metric_links]
        if not metric_ids:
            return {"metrics": [], "data": {}, "dimensions": {}}

        # 2. Parse filters
        dim_filters = {}
        if filters:
            try:
                dim_filters = json.loads(filters)
            except Exception:
                pass

        # 3. Load metric definitions
        metrics = db.query(Metric).filter(Metric.id_metric.in_(metric_ids)).all()
        metrics_by_id = {m.id_metric: m for m in metrics}

        # 4. Build metrics_info and collect all dimension ids
        metrics_info = []
        all_dim_ids = set()

        for mid in metric_ids:
            m = metrics_by_id.get(mid)
            if not m:
                continue
            dim_links = db.query(MetricDimension).filter(MetricDimension.id_metric == mid).all()
            dim_ids = [lnk.id_dimension for lnk in dim_links]
            all_dim_ids.update(dim_ids)
            metrics_info.append({
                "id_metric": m.id_metric,
                "name": m.name,
                "data_type": m.data_type,
                "description": m.description or "",
                "meta_json": _parse_json_field(m.meta_json, {}),
                "unit": m.unit or "",
                "dimension_ids": dim_ids,
            })

        # 5. Build dims_map: str(id) -> {id, name, data_type}
        dims_map = {}
        if all_dim_ids:
            dimensions = db.query(Dimension).filter(
                Dimension.id_dimension.in_(all_dim_ids)
            ).all()
            for d in dimensions:
                dims_map[str(d.id_dimension)] = {
                    "id": d.id_dimension,
                    "name": d.name,
                    "data_type": d.data_type or "str",
                }

        # 6. Load data per metric, collect unique dimension values
        data_by_metric = {}
        unique_dim_values = {str(did): set() for did in all_dim_ids}

        for mid in metric_ids:
            data_rows = db.query(MetricData).filter(MetricData.id_metric == mid).all()
            if not data_rows:
                data_by_metric[int(mid)] = []
                continue

            rows = []
            for r in data_rows:
                dims_json = _parse_json_field(r.dimensions_json, {})

                # Collect unique values before filtering
                for dk, dv in dims_json.items():
                    if dk in unique_dim_values:
                        unique_dim_values[dk].add(str(dv))

                rows.append({
                    "id_data": r.id_data,
                    "id_metric": r.id_metric,
                    "value": r.value,
                    "dimensions_json": dims_json,
                    "created_at": r.created_at.isoformat() if r.created_at else "",
                })

            data_by_metric[int(mid)] = rows

        # Add unique values to dims_map
        for dk, vals in unique_dim_values.items():
            if dk in dims_map:
                dims_map[dk]["values"] = sorted(list(vals))

        # 6.5. Aplicar derived_columns ANTES de filtrar por dimensiones temporales.
        # Cada entry: {metric_id, temporal_dim_ids: [..], configs: [..]}.
        # Los filtros estructurales (no-temporales) se aplican PRE-cálculo para
        # acotar el universo a la asignatura/curso del usuario; los temporales
        # se respetan POST-cálculo para que slope/delta vean todo el histórico
        # del estudiante. Mismo patrón que motor v2 PDF (reports.py).
        derived_columns = _parse_json_field(indicator.derived_columns, [])
        # `_matches` también lo necesitamos arriba para filtrar pre-cálculo
        def _matches(actual, expected):
            if isinstance(expected, (list, tuple, set)):
                allowed = {str(v) for v in expected}
                if not allowed:
                    return True  # filtro vacío = sin restricción
                return str(actual) in allowed
            return str(actual) == str(expected)

        if derived_columns:
            try:
                from backend.rgenerator.core.derived_fields_engine import apply_derived_fields
                import pandas as pd

                # Auto-resolver `time_ordinal_levels` desde el temporal_config del
                # indicador cuando un config slope/delta NO lo trae explícito. Esto
                # evita duplicar la lista entre temporal_config y derived_columns
                # (single source of truth en el indicador). Si el config trae su
                # propio time_ordinal_levels, ese gana (override por config).
                _temporal_cfg = _parse_json_field(indicator.temporal_config, {})
                _temporal_levels_by_label = {}
                for _lvl in (_temporal_cfg.get("levels") or []):
                    _label = _lvl.get("label")
                    _order = _lvl.get("order") or []
                    if _label and _order:
                        _temporal_levels_by_label[str(_label).lower()] = list(_order)

                def _enrich_configs(raw_configs):
                    out = []
                    for c in raw_configs:
                        if not isinstance(c, dict):
                            out.append(c)
                            continue
                        if c.get("kind") in ("slope", "delta") and c.get("time_type") == "ordinal" and not c.get("time_ordinal_levels"):
                            tf = str(c.get("time_field") or "").lower()
                            order = _temporal_levels_by_label.get(tf)
                            if order:
                                c = {**c, "time_ordinal_levels": order}
                        out.append(c)
                    return out

                for entry in derived_columns:
                    target_mid = entry.get("metric_id")
                    configs = _enrich_configs(entry.get("configs") or [])
                    temporal_dim_ids = {str(x) for x in (entry.get("temporal_dim_ids") or [])}
                    if not target_mid or not configs:
                        continue
                    rows = data_by_metric.get(int(target_mid), [])
                    if not rows:
                        continue

                    # Filtrar SOLO con filtros NO-temporales antes del cálculo
                    non_temporal_filters = {
                        k: v for k, v in (dim_filters or {}).items()
                        if str(k) not in temporal_dim_ids
                    }
                    if non_temporal_filters:
                        pre_filtered = [
                            r for r in rows
                            if all(_matches(r.get("dimensions_json", {}).get(fk, ""), fv)
                                   for fk, fv in non_temporal_filters.items())
                        ]
                    else:
                        pre_filtered = list(rows)

                    if not pre_filtered:
                        continue

                    # Construir df: value parseado (dict) + columnas con nombre humano
                    # de cada dimensión.
                    records = []
                    for r in pre_filtered:
                        val = r.get("value")
                        if isinstance(val, str):
                            try:
                                val = json.loads(val)
                            except Exception:
                                val = {}
                        rec = dict(val) if isinstance(val, dict) else {}
                        for dim_id, dim_val in (r.get("dimensions_json") or {}).items():
                            dname = dims_map.get(str(dim_id), {}).get("name")
                            if dname:
                                rec[dname] = dim_val
                        records.append(rec)
                    df = pd.DataFrame(records)

                    try:
                        df = apply_derived_fields(df, configs)
                    except Exception:
                        traceback.print_exc()
                        continue

                    # Re-inyectar columnas nuevas en value de cada row pre_filtered.
                    # Usamos posición (los rows mantienen orden con records / df).
                    new_cols = [c["name"] for c in configs if c.get("name")]
                    for i, r in enumerate(pre_filtered):
                        val = r.get("value")
                        if isinstance(val, str):
                            try:
                                val = json.loads(val)
                            except Exception:
                                val = {}
                        if not isinstance(val, dict):
                            val = {}
                        for c in new_cols:
                            if c not in df.columns:
                                continue
                            v = df.iloc[i].get(c)
                            if v is None:
                                continue
                            if isinstance(v, float) and pd.isna(v):
                                continue
                            try:
                                val[c] = float(v) if hasattr(v, "item") else v
                            except Exception:
                                val[c] = v
                        r["value"] = val
            except Exception:
                # Falla en derived_columns no debe romper el endpoint completo.
                traceback.print_exc()

        # 7. Apply dimension filters (single-value o multi-valor con list)
        # B9: si fv es list/tuple, hace IN; si es str, igualdad. Permite
        # filtros multi-select desde el frontend ({Curso: ["II A", "II B"]}).
        if dim_filters:
            for mid in data_by_metric:
                filtered = []
                for item in data_by_metric[mid]:
                    dims = item.get("dimensions_json", {})
                    match = all(
                        _matches(dims.get(fk, ""), fv)
                        for fk, fv in dim_filters.items()
                    )
                    if match:
                        filtered.append(item)
                data_by_metric[mid] = filtered

        # 7.5. Cascading dimension values: para cada dimensión D, su lista
        # de values disponibles se computa aplicando todos los filtros
        # ACTUALES excepto el de D mismo. Esto hace que los dropdowns
        # muestren solo opciones consistentes con las selecciones previas
        # (ej: si Año=2026, Asignatura solo lista las asignaturas que
        # existen en 2026), sin que el dropdown de Año pierda sus opciones
        # al estar él mismo filtrado.
        if dim_filters:
            # Re-cargar todos los rows de las metrics involucradas (sin
            # filtrar) para tener el universo completo. Esto es ligeramente
            # redundante con el paso 6 que ya cargó todo, pero allí se
            # mutó data_by_metric ya filtrado en el paso 7. Mantenemos una
            # estructura aparte para no costar memoria adicional grande.
            all_rows_by_metric = {}
            for mid in metric_ids:
                rows = db.query(MetricData.dimensions_json).filter(
                    MetricData.id_metric == mid
                ).all()
                all_rows_by_metric[mid] = [
                    _parse_json_field(r[0], {}) for r in rows
                ]

            for dim_key in list(dims_map.keys()):
                # Filtros activos sin el de la dimensión D
                other_filters = {
                    fk: fv for fk, fv in dim_filters.items() if str(fk) != str(dim_key)
                }
                values_acc = set()
                for mid, dims_list in all_rows_by_metric.items():
                    for djson in dims_list:
                        if not all(
                            _matches(djson.get(fk, ""), fv)
                            for fk, fv in other_filters.items()
                        ):
                            continue
                        v = djson.get(dim_key)
                        if v is not None and str(v) != "":
                            values_acc.add(str(v))
                dims_map[dim_key]["values"] = sorted(values_acc)

        # 8. Parse object-type values
        for mid in data_by_metric:
            m = metrics_by_id.get(mid)
            if not m:
                continue
            if m.data_type == "object":
                for item in data_by_metric[mid]:
                    val = item.get("value")
                    if isinstance(val, str):
                        try:
                            item["value"] = json.loads(val)
                        except Exception:
                            pass

        # 9-12. Extract indicator config fields
        column_roles = _parse_json_field(indicator.column_roles, {})
        filter_dimensions = _parse_json_field(indicator.filter_dimensions, [])
        temporal_config = _parse_json_field(indicator.temporal_config, {})
        role_labels = _parse_json_field(indicator.role_labels, {})
        role_formats = _parse_json_field(indicator.role_formats, {})
        achievement_levels = _parse_json_field(indicator.achievement_levels, [])

        return {
            "metrics": metrics_info,
            "dimensions": dims_map,
            "data": data_by_metric,
            "column_roles": column_roles,
            "role_labels": role_labels,
            "role_formats": role_formats,
            "filter_dimensions": filter_dimensions,
            "temporal_config": temporal_config,
            "achievement_levels": achievement_levels,
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
