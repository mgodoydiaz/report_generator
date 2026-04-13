"""
Router de demostración: genera gráficos Plotly en Python y envía el JSON
al frontend para renderizado interactivo con react-plotly.js.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import pandas as pd
import numpy as np
import json
import plotly.express as px
import plotly.graph_objects as go

from config import (
    METRICS_DB_PATH, METRIC_DATA_DB_PATH, METRIC_DIMENSIONS_DB_PATH,
    DIMENSIONS_DB_PATH, INDICATORS_DB_PATH, INDICATOR_METRICS_DB_PATH,
)
from routers._db import get_df

router = APIRouter(prefix="/api/resultspy", tags=["resultspy"])

# ── Paletas (mismas que el frontend) ─────────────────────────────────────────

CURSO_COLORS = [
    "#4361ee", "#7209b7", "#f72585", "#4cc9f0",
    "#06d6a0", "#ffd166", "#118ab2", "#073b4c",
]

LOGRO_COLORS = {
    "Adecuado": "#2a9d8f",
    "Elemental": "#e9c46a",
    "Insuficiente": "#e76f51",
}

PLOTLY_TEMPLATE = "plotly_white"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _parse_json_field(val):
    if isinstance(val, dict):
        return val
    if isinstance(val, list):
        return val
    if isinstance(val, str) and val:
        try:
            return json.loads(val.replace("'", '"'))
        except Exception:
            return {}
    return {}


def _load_indicator_data(indicator_id: int, filters: Optional[str] = None):
    """Carga y procesa datos de un indicador — lógica compartida."""
    df_rels = get_df(INDICATOR_METRICS_DB_PATH)
    metric_ids = df_rels[df_rels["id_indicator"] == indicator_id]["id_metric"].tolist()
    if not metric_ids:
        return None

    df_metrics = get_df(METRICS_DB_PATH)
    df_dims = get_df(DIMENSIONS_DB_PATH)
    df_metric_dims = get_df(METRIC_DIMENSIONS_DB_PATH)
    df_data = get_df(METRIC_DATA_DB_PATH)
    df_indicators = get_df(INDICATORS_DB_PATH)

    ind_row = df_indicators[df_indicators["id_indicator"] == indicator_id]
    if ind_row.empty:
        return None

    ind = ind_row.iloc[0]
    column_roles = _parse_json_field(ind.get("column_roles"))
    role_labels = _parse_json_field(ind.get("role_labels"))
    role_formats = _parse_json_field(ind.get("role_formats"))
    achievement_levels = _parse_json_field(ind.get("achievement_levels"))
    temporal_config = _parse_json_field(ind.get("temporal_config"))
    filter_dimensions = _parse_json_field(ind.get("filter_dimensions"))

    if not isinstance(achievement_levels, list):
        achievement_levels = []
    if not isinstance(filter_dimensions, list):
        filter_dimensions = []

    # Parsear filtros
    dim_filters = {}
    if filters:
        try:
            dim_filters = json.loads(filters)
        except Exception:
            pass

    # Construir roleMap: role -> {metric_id: column_name}
    role_map = {}
    for role, entries in column_roles.items():
        if not isinstance(entries, list):
            continue
        role_map[role] = {}
        for e in entries:
            mid = e.get("metric_id")
            col = e.get("column")
            if mid is not None and col and mid not in role_map[role]:
                role_map[role][mid] = col

    # Mapa de dimensiones
    all_dim_ids = set()
    metrics_info = {}
    for mid in metric_ids:
        row = df_metrics[df_metrics["id_metric"] == mid]
        if row.empty:
            continue
        m = row.iloc[0]
        dims = df_metric_dims[df_metric_dims["id_metric"] == mid]["id_dimension"].tolist()
        all_dim_ids.update(dims)
        metrics_info[mid] = {
            "data_type": m.get("data_type", "float"),
            "dimension_ids": dims,
            "meta_json": _parse_json_field(m.get("meta_json")),
        }

    dims_map = {}
    for _, d in df_dims.iterrows():
        did = int(d["id_dimension"])
        if did in all_dim_ids:
            dims_map[str(did)] = {"id": did, "name": d["name"], "data_type": d.get("data_type", "str")}

    # Buscar dimensión de curso, nombre
    curso_dim_id = next((k for k, v in dims_map.items() if "curso" in v["name"].lower()), None)
    nombre_dim_id = next((k for k, v in dims_map.items() if "nombre" in v["name"].lower() or "estudiante" in v["name"].lower()), None)

    # Procesar filas
    estudiantes = []
    for mid in metric_ids:
        metric_data = df_data[df_data["id_metric"] == mid]
        if metric_data.empty:
            continue
        data_type = metrics_info.get(mid, {}).get("data_type", "float")

        for _, r in metric_data.iterrows():
            djson = _parse_json_field(r.get("dimensions_json"))

            # Aplicar filtros
            if dim_filters:
                skip = False
                for fk, fv in dim_filters.items():
                    if str(djson.get(fk, "")) != str(fv):
                        skip = True
                        break
                if skip:
                    continue

            val = r.get("value")
            if data_type == "object" and isinstance(val, str):
                try:
                    val = json.loads(val)
                except Exception:
                    pass

            entry = {
                "_curso": djson.get(curso_dim_id, "") if curso_dim_id else "",
                "_nombre": djson.get(nombre_dim_id, "") if nombre_dim_id else "",
            }

            # Resolver roles
            def _resolve(role):
                col = role_map.get(role, {}).get(mid)
                if not col:
                    return None
                if isinstance(val, dict) and col in val:
                    return val[col]
                for dk, dv in djson.items():
                    dim_def = dims_map.get(dk)
                    if dim_def and dim_def["name"] == col:
                        return dv
                return None

            rend = _resolve("logro_1")
            if rend is not None:
                try:
                    entry["_rend"] = float(rend)
                except (ValueError, TypeError):
                    pass

            simce = _resolve("logro_2")
            if simce is not None:
                try:
                    entry["_simce"] = float(simce)
                except (ValueError, TypeError):
                    pass

            logro = _resolve("nivel_de_logro")
            if logro is not None:
                entry["_logro"] = logro

            hab = _resolve("habilidad")
            if hab is not None:
                entry["_habilidad"] = str(hab).capitalize()

            eval_num = _resolve("evaluacion_num")
            if eval_num is not None:
                entry["_evaluacion_num"] = eval_num

            # Temporal label
            if temporal_config and isinstance(temporal_config.get("levels"), list):
                parts = []
                for level in temporal_config["levels"]:
                    dim_id = next(
                        (k for k, v in dims_map.items() if v["name"].lower() == level.get("label", "").lower()),
                        None,
                    )
                    if dim_id and djson.get(dim_id) is not None:
                        parts.append(str(djson[dim_id]))
                if parts:
                    entry["_temporal_label"] = " / ".join(parts)

            estudiantes.append(entry)

    df = pd.DataFrame(estudiantes)

    # Recolectar valores únicos de dimensiones para filtros
    dim_values = {}
    for did_str in [str(d) for d in filter_dimensions]:
        if did_str not in dims_map:
            continue
        vals = set()
        for mid in metric_ids:
            metric_data = df_data[df_data["id_metric"] == mid]
            for _, r in metric_data.iterrows():
                dj = _parse_json_field(r.get("dimensions_json"))
                v = dj.get(did_str)
                if v is not None:
                    vals.add(str(v))
        dim_values[did_str] = sorted(vals)

    return {
        "df": df,
        "cursos": sorted(df["_curso"].dropna().unique().tolist()) if not df.empty and "_curso" in df.columns else [],
        "role_labels": role_labels,
        "role_formats": role_formats,
        "achievement_levels": achievement_levels if achievement_levels else ["Insuficiente", "Elemental", "Adecuado"],
        "temporal_config": temporal_config,
        "dims_map": dims_map,
        "filter_dimensions": filter_dimensions,
        "dim_values": dim_values,
    }


def _format_value(val, fmt_str):
    """Replica la lógica de formatValue del frontend."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    if not fmt_str:
        return f"{round(val * 100)}%"
    parts = fmt_str.split(".")
    F = parts[0]
    X = int(parts[1]) if len(parts) > 1 else 0
    if F == "T":
        return str(val)
    if F == "#":
        return f"{val:.{X}f}"
    if F == "%":
        return f"{val * 100:.{X}f}%"
    return f"{round(val * 100)}%"


# ── Endpoint: metadatos (indicadores + dimensiones para filtros) ─────────────

@router.get("/indicators")
async def list_indicators():
    df_ind = get_df(INDICATORS_DB_PATH)
    if df_ind.empty:
        return []
    result = []
    for _, row in df_ind.iterrows():
        result.append({
            "id_indicator": int(row["id_indicator"]),
            "name": row.get("name", ""),
        })
    return result


@router.get("/indicator/{indicator_id}/filters")
async def get_indicator_filters(indicator_id: int):
    """Devuelve las dimensiones de filtro con sus valores únicos."""
    data = _load_indicator_data(indicator_id)
    if data is None:
        return {"filters": []}

    filters = []
    for did_str in [str(d) for d in data["filter_dimensions"]]:
        dim = data["dims_map"].get(did_str)
        if dim and did_str in data["dim_values"]:
            filters.append({
                "id": did_str,
                "name": dim["name"],
                "values": data["dim_values"][did_str],
            })
    return {"filters": filters}


# ── Endpoint principal: genera dashboard completo ────────────────────────────

@router.get("/indicator/{indicator_id}/dashboard")
async def get_dashboard(indicator_id: int, filters: Optional[str] = Query(None)):
    try:
        data = _load_indicator_data(indicator_id, filters)
        if data is None:
            raise HTTPException(status_code=404, detail="Indicador no encontrado o sin datos")

        df = data["df"]
        cursos = data["cursos"]
        role_labels = data["role_labels"]
        role_formats = data["role_formats"]
        levels = data["achievement_levels"]
        temporal_config = data["temporal_config"]

        if df.empty:
            return {"kpis": [], "charts": []}

        has_rend = "_rend" in df.columns and df["_rend"].notna().any()
        has_simce = "_simce" in df.columns and df["_simce"].notna().any()
        has_logro = "_logro" in df.columns and df["_logro"].notna().any()
        has_habilidad = "_habilidad" in df.columns and df["_habilidad"].notna().any()
        has_temporal = "_temporal_label" in df.columns and df["_temporal_label"].notna().any()

        fmt_logro = role_formats.get("logro_1", "%.0")
        fmt_simce = role_formats.get("logro_2", "#.0")
        lbl_logro = role_labels.get("logro_1", "Logro")
        lbl_simce = role_labels.get("logro_2", "Puntaje")

        # ── KPIs ─────────────────────────────────────────────────────────────
        kpis = []
        if "_nombre" in df.columns:
            total = df["_nombre"].nunique()
        else:
            total = len(df)
        kpis.append({"label": "Total alumnos", "value": str(total), "sub": "en los cursos evaluados", "color": "indigo"})

        if has_rend:
            avg_rend = df["_rend"].mean()
            kpis.append({"label": lbl_logro + " promedio", "value": _format_value(avg_rend, fmt_logro), "sub": "rendimiento general", "color": "emerald"})

        if has_simce:
            avg_simce = df["_simce"].mean()
            kpis.append({"label": lbl_simce + " promedio", "value": _format_value(avg_simce, fmt_simce), "sub": "puntaje estimado", "color": "rose"})

        if has_logro:
            predominante = df["_logro"].mode().iloc[0] if not df["_logro"].mode().empty else "—"
            kpis.append({"label": "Nivel predominante", "value": predominante, "sub": "más frecuente", "color": "amber"})

        # ── Charts ───────────────────────────────────────────────────────────
        charts = []
        color_map = {c: CURSO_COLORS[i % len(CURSO_COLORS)] for i, c in enumerate(cursos)}

        # 1. Logro promedio por curso (bar)
        if has_rend and cursos:
            avg_by_curso = df.groupby("_curso")["_rend"].mean().reindex(cursos)
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=avg_by_curso.index.tolist(),
                y=avg_by_curso.values.tolist(),
                marker_color=[color_map.get(c, "#4361ee") for c in avg_by_curso.index],
                text=[_format_value(v, fmt_logro) for v in avg_by_curso.values],
                textposition="outside",
                textfont=dict(size=13, color="#334155"),
            ))
            is_pct = fmt_logro.startswith("%")
            fig.update_layout(
                title=None,
                template=PLOTLY_TEMPLATE,
                yaxis=dict(
                    range=[0, 1.05] if is_pct else None,
                    tickformat=".0%" if is_pct else None,
                ),
                xaxis_title=None,
                yaxis_title=lbl_logro,
                margin=dict(l=50, r=20, t=20, b=40),
                height=300,
            )
            charts.append({"id": "logro_por_curso", "title": f"{lbl_logro} Promedio por Curso", "plotly_json": fig.to_json()})

        # 2. Boxplot por curso
        if has_rend and cursos:
            fig = go.Figure()
            for i, curso in enumerate(cursos):
                vals = df[df["_curso"] == curso]["_rend"].dropna()
                fig.add_trace(go.Box(
                    y=vals.tolist(),
                    name=curso,
                    marker_color=color_map.get(curso, "#4361ee"),
                    boxmean=True,
                ))
            is_pct = fmt_logro.startswith("%")
            fig.update_layout(
                title=None,
                template=PLOTLY_TEMPLATE,
                yaxis=dict(
                    range=[0, 1.05] if is_pct else None,
                    tickformat=".0%" if is_pct else None,
                ),
                yaxis_title=lbl_logro,
                showlegend=False,
                margin=dict(l=50, r=20, t=20, b=40),
                height=300,
            )
            charts.append({"id": "boxplot_por_curso", "title": f"Distribución de {lbl_logro} por Curso", "plotly_json": fig.to_json()})

        # 3. Niveles de logro por curso (stacked bar)
        if has_logro and cursos:
            level_colors = {}
            for i, lev in enumerate(levels):
                if lev in LOGRO_COLORS:
                    level_colors[lev] = LOGRO_COLORS[lev]
                else:
                    hue = int(i / max(1, len(levels) - 1) * 120)
                    level_colors[lev] = f"hsl({hue}, 65%, 52%)"

            fig = go.Figure()
            for lev in levels:
                counts = []
                for curso in cursos:
                    n = len(df[(df["_curso"] == curso) & (df["_logro"] == lev)])
                    counts.append(n)
                fig.add_trace(go.Bar(
                    x=cursos,
                    y=counts,
                    name=lev,
                    marker_color=level_colors.get(lev, "#888"),
                    text=counts,
                    textposition="inside",
                    textfont=dict(size=11, color="white"),
                ))
            fig.update_layout(
                barmode="stack",
                title=None,
                template=PLOTLY_TEMPLATE,
                yaxis_title="Cantidad de Alumnos",
                legend=dict(orientation="h", y=-0.15),
                margin=dict(l=50, r=20, t=20, b=60),
                height=320,
            )
            charts.append({"id": "niveles_por_curso", "title": "Niveles de Logro por Curso", "plotly_json": fig.to_json()})

        # 4. Distribución de niveles (pie)
        if has_logro:
            level_counts = df["_logro"].value_counts()
            ordered_levels = [l for l in levels if l in level_counts.index]
            colors = [LOGRO_COLORS.get(l, "#888") for l in ordered_levels]
            fig = go.Figure(go.Pie(
                labels=ordered_levels,
                values=[int(level_counts[l]) for l in ordered_levels],
                marker=dict(colors=colors),
                textinfo="label+percent+value",
                textfont=dict(size=13),
                hole=0.35,
            ))
            fig.update_layout(
                title=None,
                template=PLOTLY_TEMPLATE,
                margin=dict(l=20, r=20, t=20, b=20),
                height=320,
            )
            charts.append({"id": "distribucion_niveles", "title": "Distribución General de Niveles", "plotly_json": fig.to_json()})

        # 5. Habilidades (horizontal bar)
        if has_habilidad and "_rend" in df.columns:
            hab_avg = df.groupby("_habilidad")["_rend"].mean().sort_values(ascending=True)
            fig = go.Figure(go.Bar(
                x=hab_avg.values.tolist(),
                y=[h.capitalize() for h in hab_avg.index],
                orientation="h",
                marker_color="#4361ee",
                text=[_format_value(v, fmt_logro) for v in hab_avg.values],
                textposition="inside",
                insidetextanchor="end",
                textfont=dict(size=12, color="white"),
                constraintext="none",
            ))
            is_pct = fmt_logro.startswith("%")
            fig.update_layout(
                title=None,
                template=PLOTLY_TEMPLATE,
                xaxis=dict(
                    range=[0, 1.15] if is_pct else None,
                    tickformat=".0%" if is_pct else None,
                ),
                xaxis_title=lbl_logro,
                margin=dict(l=160, r=20, t=20, b=40),
                height=max(250, len(hab_avg) * 40),
            )
            charts.append({"id": "habilidades", "title": f"{lbl_logro} por Habilidad", "plotly_json": fig.to_json()})

        # 6. Radar de habilidades por curso
        if has_habilidad and cursos and "_rend" in df.columns:
            habs = sorted(df["_habilidad"].dropna().unique())
            if len(habs) >= 3:
                fig = go.Figure()
                for i, curso in enumerate(cursos):
                    vals = []
                    for h in habs:
                        subset = df[(df["_habilidad"] == h) & (df["_curso"] == curso)]["_rend"]
                        vals.append(subset.mean() if len(subset) else 0)
                    vals.append(vals[0])  # cerrar el radar
                    fig.add_trace(go.Scatterpolar(
                        r=vals,
                        theta=[h.capitalize() for h in habs] + [habs[0].capitalize()],
                        name=curso,
                        line=dict(color=color_map.get(curso, CURSO_COLORS[i % len(CURSO_COLORS)]), width=2),
                        fill="toself",
                        fillcolor=color_map.get(curso, CURSO_COLORS[i % len(CURSO_COLORS)]),
                        opacity=0.3,
                    ))
                is_pct = fmt_logro.startswith("%")
                fig.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 1] if is_pct else None,
                            tickformat=".0%" if is_pct else None,
                        ),
                    ),
                    title=None,
                    template=PLOTLY_TEMPLATE,
                    margin=dict(l=60, r=60, t=30, b=30),
                    height=360,
                )
                charts.append({"id": "radar_habilidades", "title": "Radar de Habilidades por Curso", "plotly_json": fig.to_json()})

        # 7. Tendencia temporal (line)
        if has_rend and has_temporal and cursos:
            temporal_df = df.dropna(subset=["_temporal_label", "_rend"])
            if not temporal_df.empty:
                # Ordenar evaluaciones
                eval_order = temporal_df.drop_duplicates("_temporal_label").sort_values(
                    "_evaluacion_num" if "_evaluacion_num" in temporal_df.columns else "_temporal_label"
                )["_temporal_label"].tolist()

                fig = go.Figure()
                for i, curso in enumerate(cursos):
                    sub = temporal_df[temporal_df["_curso"] == curso]
                    avgs = sub.groupby("_temporal_label")["_rend"].mean().reindex(eval_order)
                    fig.add_trace(go.Scatter(
                        x=eval_order,
                        y=avgs.values.tolist(),
                        mode="lines+markers",
                        name=curso,
                        line=dict(color=color_map.get(curso, CURSO_COLORS[i % len(CURSO_COLORS)]), width=2.5),
                        marker=dict(size=8),
                        connectgaps=True,
                    ))
                is_pct = fmt_logro.startswith("%")
                fig.update_layout(
                    title=None,
                    template=PLOTLY_TEMPLATE,
                    yaxis=dict(
                        range=[0, 1.05] if is_pct else None,
                        tickformat=".0%" if is_pct else None,
                    ),
                    yaxis_title=lbl_logro,
                    xaxis_title="Evaluación",
                    legend=dict(orientation="h", y=-0.2),
                    margin=dict(l=50, r=20, t=20, b=60),
                    height=320,
                )
                charts.append({"id": "tendencia_temporal", "title": "Tendencia Temporal por Curso", "plotly_json": fig.to_json()})

        # 8. Niveles por curso y evaluación (stacked bar agrupado)
        if has_logro and has_temporal and cursos:
            temporal_df = df.dropna(subset=["_temporal_label", "_logro"])
            if not temporal_df.empty:
                eval_order = temporal_df.drop_duplicates("_temporal_label").sort_values(
                    "_evaluacion_num" if "_evaluacion_num" in temporal_df.columns else "_temporal_label"
                )["_temporal_label"].tolist()

                level_colors = {}
                for i, lev in enumerate(levels):
                    if lev in LOGRO_COLORS:
                        level_colors[lev] = LOGRO_COLORS[lev]
                    else:
                        hue = int(i / max(1, len(levels) - 1) * 120)
                        level_colors[lev] = f"hsl({hue}, 65%, 52%)"

                x_labels = []
                level_data = {lev: [] for lev in levels}
                for curso in cursos:
                    for ev in eval_order:
                        subset = temporal_df[(temporal_df["_curso"] == curso) & (temporal_df["_temporal_label"] == ev)]
                        x_labels.append(f"{curso}<br>{ev}")
                        for lev in levels:
                            level_data[lev].append(int(len(subset[subset["_logro"] == lev])))

                fig = go.Figure()
                for lev in levels:
                    fig.add_trace(go.Bar(
                        x=x_labels,
                        y=level_data[lev],
                        name=lev,
                        marker_color=level_colors.get(lev, "#888"),
                        text=level_data[lev],
                        textposition="inside",
                        textfont=dict(size=10, color="white"),
                    ))
                fig.update_layout(
                    barmode="stack",
                    title=None,
                    template=PLOTLY_TEMPLATE,
                    yaxis_title="Cantidad",
                    xaxis_tickangle=-35,
                    legend=dict(orientation="h", y=-0.25),
                    margin=dict(l=50, r=20, t=20, b=80),
                    height=380,
                )
                charts.append({"id": "niveles_por_curso_y_mes", "title": "Niveles por Curso y Evaluación", "plotly_json": fig.to_json()})

        # 9. Tabla resumen por curso (como datos JSON, no gráfico)
        if cursos and has_rend:
            tabla_rows = []
            for curso in cursos:
                sub = df[df["_curso"] == curso]
                row = {
                    "Curso": curso,
                    "N° Alumnos": int(sub["_nombre"].nunique()) if "_nombre" in sub.columns else len(sub),
                }
                if has_rend:
                    row[lbl_logro] = _format_value(sub["_rend"].mean(), fmt_logro)
                    row["Mín"] = _format_value(sub["_rend"].min(), fmt_logro)
                    row["Máx"] = _format_value(sub["_rend"].max(), fmt_logro)
                if has_simce:
                    row[lbl_simce] = _format_value(sub["_simce"].mean(), fmt_simce)
                if has_logro:
                    for lev in levels:
                        row[lev] = int(len(sub[sub["_logro"] == lev]))
                tabla_rows.append(row)
            charts.append({"id": "tabla_resumen", "title": "Resumen por Curso", "table_data": tabla_rows})

        return {"kpis": kpis, "charts": charts}

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
