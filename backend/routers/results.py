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

        # 7. Apply dimension filters
        if dim_filters:
            for mid in data_by_metric:
                filtered = []
                for item in data_by_metric[mid]:
                    dims = item.get("dimensions_json", {})
                    match = all(
                        str(dims.get(fk, "")) == str(fv)
                        for fk, fv in dim_filters.items()
                    )
                    if match:
                        filtered.append(item)
                data_by_metric[mid] = filtered

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
