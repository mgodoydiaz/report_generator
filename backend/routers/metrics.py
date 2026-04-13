import json
import io
from datetime import datetime
from typing import List, Optional, Dict, Any

import pandas as pd
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import get_current_user
from backend.models import User, Metric, MetricDimension, MetricData, Dimension

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


# --- Models ---
class MetricBase(BaseModel):
    name: str
    data_type: str = "float"
    description: Optional[str] = ""
    meta_json: Optional[Dict[str, Any]] = {}


class MetricCreate(MetricBase):
    dimension_ids: List[int] = []


class MetricUpdate(MetricBase):
    dimension_ids: Optional[List[int]] = None


class MetricDataPoint(BaseModel):
    value: Any
    dimensions_json: Dict[str, Any]


class BatchDeleteRequest(BaseModel):
    ids: List[int]


# --- Helpers ---
def _parse_meta_json(raw) -> dict:
    if isinstance(raw, str) and raw:
        try:
            return json.loads(raw.replace("'", '"'))
        except Exception:
            return {}
    if isinstance(raw, dict):
        return raw
    return {}


def _parse_dims_json(raw) -> dict:
    if isinstance(raw, str) and raw:
        try:
            return json.loads(raw.replace("'", '"'))
        except Exception:
            return {}
    if isinstance(raw, dict):
        return raw
    return {}


def _metric_to_dict(m: Metric) -> dict:
    dim_ids = [lnk.id_dimension for lnk in m.dimension_links]
    return {
        "id_metric": m.id_metric,
        "name": m.name,
        "data_type": m.data_type,
        "description": m.description or "",
        "meta_json": _parse_meta_json(m.meta_json),
        "unit": m.unit or "",
        "updated_at": m.updated_at.strftime("%Y-%m-%d %H:%M:%S") if m.updated_at else "",
        "dimension_ids": dim_ids,
    }


# --- Endpoints: Metrics Definitions ---

@router.get("/")
async def get_metrics(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        metrics = db.query(Metric).filter(Metric.org_id == user.org_id).all()
        return [_metric_to_dict(m) for m in metrics]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_metric(
    metric: MetricCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        new_m = Metric(
            name=metric.name,
            data_type=metric.data_type,
            description=metric.description or "",
            meta_json=json.dumps(metric.meta_json) if metric.meta_json else "{}",
            updated_at=datetime.utcnow(),
            org_id=user.org_id,
        )
        db.add(new_m)
        db.flush()

        for dim_id in metric.dimension_ids:
            db.add(MetricDimension(id_metric=new_m.id_metric, id_dimension=dim_id))

        db.commit()
        db.refresh(new_m)

        return {"status": "success", "data": _metric_to_dict(new_m)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{metric_id}")
async def update_metric(
    metric_id: int,
    metric: MetricUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        record = db.query(Metric).filter(
            Metric.id_metric == metric_id,
            Metric.org_id == user.org_id,
        ).first()
        if not record:
            raise HTTPException(status_code=404, detail="Métrica no encontrada")

        record.name = metric.name
        record.data_type = metric.data_type
        if metric.description is not None:
            record.description = metric.description
        if metric.meta_json is not None:
            record.meta_json = json.dumps(metric.meta_json)
        record.updated_at = datetime.utcnow()

        if metric.dimension_ids is not None:
            db.query(MetricDimension).filter(
                MetricDimension.id_metric == metric_id
            ).delete(synchronize_session=False)
            for dim_id in metric.dimension_ids:
                db.add(MetricDimension(id_metric=metric_id, id_dimension=dim_id))

        db.commit()
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{metric_id}")
async def delete_metric(
    metric_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        record = db.query(Metric).filter(
            Metric.id_metric == metric_id,
            Metric.org_id == user.org_id,
        ).first()
        if record:
            db.delete(record)  # cascade deletes MetricDimension, MetricData
            db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# --- Endpoints: Metric Data values ---

@router.get("/{metric_id}/data")
async def get_metric_data(
    metric_id: int,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        # Verify ownership via metric
        metric = db.query(Metric).filter(
            Metric.id_metric == metric_id,
            Metric.org_id == user.org_id,
        ).first()
        if not metric:
            raise HTTPException(status_code=404, detail="Métrica no encontrada")

        total = db.query(MetricData).filter(MetricData.id_metric == metric_id).count()

        offset = (page - 1) * page_size
        rows = (
            db.query(MetricData)
            .filter(MetricData.id_metric == metric_id)
            .offset(offset)
            .limit(page_size)
            .all()
        )

        results = []
        for r in rows:
            item = {
                "id_data": r.id_data,
                "id_metric": r.id_metric,
                "value": r.value,
                "dimensions_json": _parse_dims_json(r.dimensions_json),
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            results.append(item)

        return {"items": results, "total": total}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{metric_id}/data")
async def add_metric_data_point(
    metric_id: int,
    point: MetricDataPoint,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        metric = db.query(Metric).filter(
            Metric.id_metric == metric_id,
            Metric.org_id == user.org_id,
        ).first()
        if not metric:
            raise HTTPException(status_code=404, detail="Métrica no encontrada")

        final_val = point.value
        if isinstance(final_val, (dict, list)):
            final_val = json.dumps(final_val)
        else:
            final_val = str(final_val) if final_val is not None else None

        new_dp = MetricData(
            id_metric=metric_id,
            value=final_val,
            dimensions_json=json.dumps(point.dimensions_json),
            created_at=datetime.utcnow(),
            org_id=user.org_id,
        )
        db.add(new_dp)
        db.commit()
        db.refresh(new_dp)

        return {
            "status": "success",
            "data": {
                "id_data": new_dp.id_data,
                "id_metric": new_dp.id_metric,
                "value": new_dp.value,
                "dimensions_json": _parse_dims_json(new_dp.dimensions_json),
                "created_at": new_dp.created_at.isoformat() if new_dp.created_at else "",
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{metric_id}/clear")
async def clear_metric_data(
    metric_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        metric = db.query(Metric).filter(
            Metric.id_metric == metric_id,
            Metric.org_id == user.org_id,
        ).first()
        if not metric:
            raise HTTPException(status_code=404, detail="Métrica no encontrada")

        deleted = (
            db.query(MetricData)
            .filter(MetricData.id_metric == metric_id)
            .delete(synchronize_session=False)
        )
        db.commit()
        return {"status": "success", "cleared_count": deleted}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/data/{data_id}")
async def delete_data_point(
    data_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        record = db.query(MetricData).filter(MetricData.id_data == data_id).first()
        if record:
            # Verify org via metric
            metric = db.query(Metric).filter(
                Metric.id_metric == record.id_metric,
                Metric.org_id == user.org_id,
            ).first()
            if not metric:
                raise HTTPException(status_code=403, detail="Acceso denegado")
            db.delete(record)
            db.commit()
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/data/{data_id}")
async def update_metric_data(
    data_id: int,
    point: MetricDataPoint,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        record = db.query(MetricData).filter(MetricData.id_data == data_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="Data point not found")

        # Verify org via metric
        metric = db.query(Metric).filter(
            Metric.id_metric == record.id_metric,
            Metric.org_id == user.org_id,
        ).first()
        if not metric:
            raise HTTPException(status_code=403, detail="Acceso denegado")

        final_val = point.value
        if isinstance(final_val, (dict, list)):
            final_val = json.dumps(final_val)
        else:
            final_val = str(final_val) if final_val is not None else None

        record.value = final_val
        record.dimensions_json = json.dumps(point.dimensions_json) if isinstance(point.dimensions_json, dict) else point.dimensions_json
        db.commit()
        return {"status": "success", "id_data": data_id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data/batch-delete")
async def delete_metric_data_batch(
    req: BatchDeleteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        # Only delete data points that belong to metrics owned by this org
        org_metric_ids = [
            m.id_metric
            for m in db.query(Metric.id_metric).filter(Metric.org_id == user.org_id).all()
        ]
        deleted = (
            db.query(MetricData)
            .filter(
                MetricData.id_data.in_(req.ids),
                MetricData.id_metric.in_(org_metric_ids),
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        return {"status": "success", "deleted_count": deleted}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{metric_id}/export")
async def export_metric_data(
    metric_id: int,
    format: str = "excel",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        metric = db.query(Metric).filter(
            Metric.id_metric == metric_id,
            Metric.org_id == user.org_id,
        ).first()
        if not metric:
            raise HTTPException(status_code=404, detail="Métrica no encontrada")

        meta = _parse_meta_json(metric.meta_json)

        # Build dims_map: id_dimension -> name
        dim_links = db.query(MetricDimension).filter(MetricDimension.id_metric == metric_id).all()
        dim_ids = [lnk.id_dimension for lnk in dim_links]
        dims = db.query(Dimension).filter(Dimension.id_dimension.in_(dim_ids)).all()
        dims_map = {d.id_dimension: d.name for d in dims}

        data_rows = db.query(MetricData).filter(MetricData.id_metric == metric_id).all()

        flat_data = []
        for r in data_rows:
            item = {}
            dims_json = _parse_dims_json(r.dimensions_json)
            for dim_id_str, val in dims_json.items():
                dim_name = dims_map.get(int(dim_id_str), f"Dim_{dim_id_str}")
                item[dim_name] = val

            value = r.value
            if metric.data_type == "object":
                try:
                    val_obj = json.loads(value) if isinstance(value, str) else (value or {})
                    for k, v in val_obj.items():
                        item[k] = v
                except Exception:
                    item["Valor_Raw"] = str(value)
            else:
                item[metric.name] = value

            flat_data.append(item)

        df_export = pd.DataFrame(flat_data)
        stream = io.BytesIO()

        if format == "excel":
            with pd.ExcelWriter(stream, engine="openpyxl") as writer:
                df_export.to_excel(writer, index=False, sheet_name="Datos")
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename_ext = "xlsx"
        elif format == "csv":
            df_export.to_csv(stream, index=False, sep=";", encoding="utf-8-sig")
            media_type = "text/csv"
            filename_ext = "csv"
        elif format == "txt":
            df_export.to_csv(stream, index=False, sep="\t", encoding="utf-8")
            media_type = "text/plain"
            filename_ext = "txt"
        else:
            raise HTTPException(status_code=400, detail="Formato no soportado")

        stream.seek(0)
        return StreamingResponse(
            stream,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename=export.{filename_ext}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{metric_id}/distinct/{column}")
async def get_metric_distinct_values(
    metric_id: int,
    column: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        metric = db.query(Metric).filter(
            Metric.id_metric == metric_id,
            Metric.org_id == user.org_id,
        ).first()
        if not metric:
            return {"values": []}

        dim_links = db.query(MetricDimension).filter(MetricDimension.id_metric == metric_id).all()
        dim_ids = [lnk.id_dimension for lnk in dim_links]
        dims = db.query(Dimension).filter(Dimension.id_dimension.in_(dim_ids)).all()
        dims_map = {d.id_dimension: d.name for d in dims}

        data_rows = db.query(MetricData).filter(MetricData.id_metric == metric_id).all()

        distinct_vals = set()
        for r in data_rows:
            dims_json = _parse_dims_json(r.dimensions_json)
            for dim_id_str, val in dims_json.items():
                dim_name = dims_map.get(int(dim_id_str), f"Dim_{dim_id_str}")
                if dim_name == column:
                    distinct_vals.add(str(val))

            value = r.value
            if metric.data_type == "object":
                try:
                    val_obj = json.loads(value) if isinstance(value, str) else {}
                    for k, v in val_obj.items():
                        if k == column:
                            distinct_vals.add(str(v))
                except Exception:
                    if column == "Valor_Raw":
                        distinct_vals.add(str(value))
            elif metric.name == column:
                distinct_vals.add(str(value))

        return {"values": sorted(list(distinct_vals))}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{metric_id}/template")
async def get_metric_template(
    metric_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        metric = db.query(Metric).filter(
            Metric.id_metric == metric_id,
            Metric.org_id == user.org_id,
        ).first()
        if not metric:
            raise HTTPException(status_code=404, detail="Métrica no encontrada")

        meta = _parse_meta_json(metric.meta_json)

        dim_links = db.query(MetricDimension).filter(MetricDimension.id_metric == metric_id).all()
        dim_ids = [lnk.id_dimension for lnk in dim_links]
        dims = db.query(Dimension).filter(Dimension.id_dimension.in_(dim_ids)).all()
        dim_names = [d.name for d in dims]

        columns = list(dim_names)
        if metric.data_type == "object" and meta.get("fields"):
            for f in meta["fields"]:
                columns.append(f["name"])
        else:
            columns.append(metric.name)

        df_template = pd.DataFrame(columns=columns)
        stream = io.BytesIO()
        with pd.ExcelWriter(stream, engine="openpyxl") as writer:
            df_template.to_excel(writer, index=False, sheet_name="Plantilla")
        stream.seek(0)

        filename = f"Plantilla_{metric.name.replace(' ', '_')}.xlsx"
        return StreamingResponse(
            stream,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{metric_id}/import")
async def import_metric_data(
    metric_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        metric = db.query(Metric).filter(
            Metric.id_metric == metric_id,
            Metric.org_id == user.org_id,
        ).first()
        if not metric:
            raise HTTPException(status_code=404, detail="Métrica no encontrada")

        meta = _parse_meta_json(metric.meta_json)

        # Build dim_name -> id map
        dim_links = db.query(MetricDimension).filter(MetricDimension.id_metric == metric_id).all()
        dim_ids = [lnk.id_dimension for lnk in dim_links]
        dims = db.query(Dimension).filter(Dimension.id_dimension.in_(dim_ids)).all()
        dim_name_to_id = {d.name: d.id_dimension for d in dims}

        new_data_points = []

        for file in files:
            contents = await file.read()
            if file.filename.endswith(".csv"):
                df = pd.read_csv(io.BytesIO(contents), sep=";")
            else:
                df = pd.read_excel(io.BytesIO(contents))

            for _, row in df.iterrows():
                dims_json = {}
                for dim_name, dim_id in dim_name_to_id.items():
                    if dim_name in df.columns:
                        val = row[dim_name]
                        if pd.notna(val):
                            dims_json[str(dim_id)] = str(val)

                final_value = None
                if metric.data_type == "object":
                    val_obj = {}
                    fields = meta.get("fields", [])
                    for f in fields:
                        fname = f["name"]
                        if fname in df.columns:
                            val = row[fname]
                            if pd.notna(val):
                                if f["type"] == "int":
                                    try: val = int(val)
                                    except Exception: pass
                                elif f["type"] == "float":
                                    try: val = float(val)
                                    except Exception: pass
                                val_obj[fname] = val
                    final_value = json.dumps(val_obj)
                else:
                    value_col = metric.name
                    if value_col in df.columns:
                        v = row[value_col]
                        if pd.notna(v):
                            if metric.data_type == "int":
                                final_value = str(int(v))
                            elif metric.data_type == "float":
                                final_value = str(float(v))
                            else:
                                final_value = str(v)

                if final_value is not None:
                    new_data_points.append(MetricData(
                        id_metric=metric_id,
                        value=final_value,
                        dimensions_json=json.dumps(dims_json),
                        created_at=datetime.utcnow(),
                        org_id=user.org_id,
                    ))

        if new_data_points:
            db.add_all(new_data_points)
            db.commit()

        return {"status": "success", "imported": len(new_data_points)}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(e)
        raise HTTPException(status_code=500, detail=str(e))
