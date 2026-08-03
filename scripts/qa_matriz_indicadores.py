#!/usr/bin/env python
"""
qa_matriz_indicadores.py — Matriz de estado (ETL / datos / dashboard / informes)
por indicador de una organización.

Es una herramienta de QA de SOLO LECTURA sobre los datos de negocio: lo único
que escribe son (a) el usuario admin de QA que necesita para autenticarse
contra la API (idempotente: si ya existe, solo le resetea la clave) y (b) los
archivos de salida (PDFs + matriz.json + markdown). No toca `metric_data`,
`indicators`, `pipelines` ni `specs`.

Qué revisa, por indicador:

  1. ETL      — qué pipelines de la tabla `pipelines` le corresponden (la
                asociación fuerte es por `metric_id` dentro de `config_json`;
                si no hay, se intenta por nombre y se marca como débil),
                si `config_json` parsea y si `last_run` tiene valor.
  2. Datos    — filas en `metric_data` por métrica, última carga (`created_at`),
                última evaluación resuelta con el MISMO resolver que usan los
                informes (`rgenerator/reports/periodos.py`), y auditoría de las
                dimensiones de tipo fecha (`dimensions.data_type == 'date'`).
  3. Dashboard— `dashboard_layout` parsea, cuántos items tiene, que cada
                `configured_chart` / `configured_table` exista como Spec del
                tipo correcto, y si `/api/charts/{id}/data` /
                `/api/tables/{id}/data` devuelven datos o vienen vacíos.
  4. Informes — `GET /api/indicators/{id}/report-options` (qué cards expone y
                cuáles vienen deshabilitadas y por qué) y luego un
                `POST /api/indicators/{id}/export-pdf` por cada modo de período
                más los informes especializados de `reports/custom/`
                (`POST /api/reports/custom/{nombre}`). Cada PDF generado se
                guarda en el directorio de salida para revisión visual.

Clasificación de cada intento de informe:

    ok             200 + PDF con >0 páginas (verificado con PyMuPDF)
    ok_vacio       200 pero el PDF no abre o tiene 0 páginas
    400_esperado   4xx cuyo motivo es coherente con la cobertura de datos
                   (report-options ya deshabilitó la card, o el resolver de
                   períodos dice que ese período no tiene datos)
    400_sorpresa   4xx que NADIE anticipó (report-options decía disponible y
                   el resolver también) → hallazgo real
    500            error del servidor
    timeout        el request excedió --timeout

Uso (el camino soportado es correrlo DENTRO del contenedor backend de dev,
donde `DATABASE_URL` ya apunta a la DB canónica y la API vive en :8000):

    docker compose -f docker-compose.dev.yml exec -T backend \\
        python scripts/qa_matriz_indicadores.py --org 1 \\
               --base-url http://localhost:8000

Desde el host (WSL) hay que pasar el DATABASE_URL correcto a mano; OJO que
`localhost:5432` NO es la DB de dev (ver memory/project_entorno_tres_postgres).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

# ── Bootstrap de imports: el paquete se importa SIEMPRE como backend.* ──
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# =========================================================================
# Utilidades
# =========================================================================

OK = "✅"
WARN = "⚠️"
BAD = "❌"
NA = "—"


def _slug(texto: str) -> str:
    """Nombre de archivo seguro a partir de un texto libre."""
    base = unicodedata.normalize("NFKD", str(texto or ""))
    base = base.encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^A-Za-z0-9]+", "_", base).strip("_").lower()
    return base or "sin_nombre"


def _corto(texto: Any, n: int = 120) -> str:
    t = " ".join(str(texto or "").split())
    return t if len(t) <= n else t[: n - 1] + "…"


def _celda_md(texto: Any) -> str:
    """Escapa lo que rompe una celda de tabla markdown."""
    return _corto(texto, 160).replace("|", "/").replace("\n", " ")


def _json_seguro(valor: Any, default: Any):
    if isinstance(valor, (dict, list)):
        return valor
    if not valor:
        return default
    try:
        return json.loads(valor)
    except Exception:
        return None  # None ⇒ "no parsea" (distinto de vacío)


# =========================================================================
# Cliente HTTP mínimo
# =========================================================================

class ApiClient:
    def __init__(self, base_url: str, timeout: int):
        import requests

        self._requests = requests
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.token: Optional[str] = None

    def login(self, email: str, password: str) -> dict:
        r = self.session.post(
            f"{self.base}/api/auth/login",
            json={"email": email, "password": password},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        self.token = data["access_token"]
        self.session.headers["Authorization"] = f"Bearer {self.token}"
        return data["user"]

    def get(self, path: str, **kw):
        return self.session.get(f"{self.base}{path}", timeout=self.timeout, **kw)

    def post(self, path: str, **kw):
        return self.session.post(f"{self.base}{path}", timeout=self.timeout, **kw)


# =========================================================================
# 1. ETL — asociación indicador ↔ pipelines
# =========================================================================

_STOPWORDS = {
    "de", "del", "la", "el", "los", "las", "por", "para", "y", "carga",
    "proceso", "pipeline", "ia", "prueba", "nuevo", "resultados",
}


def _tokens_nombre(texto: str) -> set[str]:
    base = unicodedata.normalize("NFKD", str(texto or "").lower())
    base = base.encode("ascii", "ignore").decode("ascii")
    return {t for t in re.split(r"[^a-z0-9]+", base) if len(t) > 2 and t not in _STOPWORDS}


def _metric_ids_en_config(cfg: Any) -> set[int]:
    """Todos los `metric_id` / `id_metric` que aparezcan en el JSON, a cualquier nivel."""
    encontrados: set[int] = set()

    def _walk(nodo):
        if isinstance(nodo, dict):
            for k, v in nodo.items():
                if k in ("metric_id", "id_metric"):
                    if isinstance(v, int):
                        encontrados.add(v)
                    elif isinstance(v, list):
                        encontrados.update(x for x in v if isinstance(x, int))
                    elif isinstance(v, str) and v.isdigit():
                        encontrados.add(int(v))
                else:
                    _walk(v)
        elif isinstance(nodo, list):
            for x in nodo:
                _walk(x)

    _walk(cfg)
    return encontrados


def analizar_pipelines(db, org_id: int) -> list[dict]:
    """Radiografía de todos los pipelines de la org (parseo + metric_ids)."""
    from backend.models import Pipeline

    filas = []
    for p in db.query(Pipeline).filter(Pipeline.org_id == org_id).order_by(
        Pipeline.pipeline_id
    ).all():
        crudo = p.config_json or ""
        try:
            cfg = json.loads(crudo) if crudo.strip() else {}
            parsea, error = True, None
        except Exception as e:
            cfg, parsea, error = {}, False, f"{type(e).__name__}: {e}"
        pasos = cfg.get("pipeline") or []
        filas.append({
            "pipeline_id": p.pipeline_id,
            "nombre": p.pipeline,
            "description": _corto(p.description, 200),
            "hidden": bool(p.hidden),
            "config_json_parsea": parsea,
            "config_json_error": error,
            "config_json_bytes": len(crudo),
            "n_steps": len(pasos),
            "steps": [s.get("step") for s in pasos if isinstance(s, dict)],
            "metric_ids": sorted(_metric_ids_en_config(cfg)),
            "last_run": p.last_run.isoformat() if p.last_run else None,
            "tokens": _tokens_nombre(f"{p.pipeline} {p.description or ''}"),
        })
    return filas


def etl_de_indicador(indicador: dict, pipelines: list[dict]) -> dict:
    """Asocia pipelines al indicador; explicita cómo se derivó la relación."""
    metric_ids = set(indicador["metric_ids"])
    tokens_ind = _tokens_nombre(indicador["name"])

    fuertes, debiles = [], []
    for p in pipelines:
        comunes = metric_ids & set(p["metric_ids"])
        if comunes:
            fuertes.append({
                **p, "_match": "metric_id", "_metricas_comunes": sorted(comunes),
                # Relación fuerte por dato pero con nombres que no se parecen
                # en nada: casi siempre significa que uno de los dos quedó mal
                # bautizado tras una refactorización.
                "_nombre_divergente": not bool(tokens_ind & p["tokens"]),
                "_metricas_no_consumidas": sorted(set(p["metric_ids"]) - metric_ids),
            })
            continue
        if tokens_ind and tokens_ind & p["tokens"]:
            debiles.append({**p, "_match": "nombre", "_tokens_comunes": sorted(tokens_ind & p["tokens"])})

    asociados = fuertes or debiles
    if fuertes:
        criterio = "metric_id en config_json"
    elif debiles:
        criterio = "coincidencia de nombre (DÉBIL — verificar a mano)"
    else:
        criterio = "sin asociación clara"

    detalle = []
    for p in asociados:
        detalle.append({
            "pipeline_id": p["pipeline_id"],
            "nombre": p["nombre"],
            "match": p["_match"],
            "metricas_comunes": p.get("_metricas_comunes"),
            "tokens_comunes": p.get("_tokens_comunes"),
            "nombre_divergente": p.get("_nombre_divergente", False),
            "metricas_no_consumidas": p.get("_metricas_no_consumidas") or [],
            "config_json_parsea": p["config_json_parsea"],
            "config_json_error": p["config_json_error"],
            "n_steps": p["n_steps"],
            "last_run": p["last_run"],
            "hidden": p["hidden"],
        })

    if not asociados:
        estado, nota = BAD, "sin pipeline asociado"
    else:
        malos = [d for d in detalle if not d["config_json_parsea"]]
        sin_run = [d for d in detalle if not d["last_run"]]
        nombres = ", ".join(f"#{d['pipeline_id']} {d['nombre']}" for d in detalle)
        if malos:
            estado, nota = BAD, f"config_json no parsea en {', '.join(str(d['pipeline_id']) for d in malos)}"
        elif not fuertes:
            estado, nota = WARN, f"asociación por nombre (verificar): {nombres}"
        elif sin_run:
            estado, nota = WARN, f"{nombres} — sin last_run"
        else:
            ult = max(d["last_run"] for d in detalle)
            estado, nota = OK, f"{nombres} — last_run {ult[:10]}"

    return {
        "criterio_asociacion": criterio,
        "pipelines": detalle,
        "estado": estado,
        "nota": nota,
    }


# =========================================================================
# 2. Datos
# =========================================================================

# `dimensions.data_type` que declara una columna como fecha real.
def _tipos_fecha() -> frozenset:
    from backend.rgenerator.reports.periodos import TIPOS_DATO_FECHA
    return TIPOS_DATO_FECHA


def _parece_fecha_por_nombre(nombre: str) -> bool:
    base = unicodedata.normalize("NFKD", str(nombre or "").lower())
    base = base.encode("ascii", "ignore").decode("ascii")
    return any(t in re.split(r"[^a-z0-9]+", base) for t in ("fecha", "fechas", "date", "dates"))


def datos_de_indicador(db, indicador: dict, org_id: int, dfs: dict) -> dict:
    """Filas por métrica, última carga, última evaluación y auditoría de dims fecha."""
    from backend.models import Dimension, Metric, MetricData, MetricDimension
    from backend.rgenerator.reports.periodos import (
        clave_temporal,
        detectar_columnas_temporales_df,
        resolver_periodo_multi,
    )
    from sqlalchemy import func

    metricas = []
    total_filas = 0
    ultima_carga = None
    for mid in indicador["metric_ids"]:
        m = db.query(Metric).filter(Metric.id_metric == mid).first()
        if m is None:
            metricas.append({"id_metric": mid, "name": None, "error": "métrica inexistente"})
            continue
        filas = db.query(func.count(MetricData.id_data)).filter(
            MetricData.id_metric == mid
        ).scalar() or 0
        creada = db.query(func.max(MetricData.created_at)).filter(
            MetricData.id_metric == mid
        ).scalar()
        dim_ids = [l.id_dimension for l in db.query(MetricDimension).filter(
            MetricDimension.id_metric == mid
        ).all()]
        dims = db.query(Dimension).filter(Dimension.id_dimension.in_(dim_ids)).all() if dim_ids else []
        total_filas += filas
        if creada and (ultima_carga is None or creada > ultima_carga):
            ultima_carga = creada
        metricas.append({
            "id_metric": mid,
            "name": m.name,
            "org_id": m.org_id,
            "filas_metric_data": filas,
            "ultima_created_at": creada.isoformat() if creada else None,
            "dimensiones": [
                {"id": d.id_dimension, "name": d.name, "data_type": d.data_type or "str"}
                for d in sorted(dims, key=lambda x: x.id_dimension)
            ],
        })

    # ── Dimensiones tipo fecha ──
    tipos_fecha = _tipos_fecha()
    todas_dims = {}
    for m in metricas:
        for d in m.get("dimensiones", []):
            todas_dims[d["id"]] = d
    dims_fecha_marcadas = [d for d in todas_dims.values() if (d["data_type"] or "").lower() in tipos_fecha]
    dims_fecha_sin_marcar = [
        d for d in todas_dims.values()
        if _parece_fecha_por_nombre(d["name"]) and (d["data_type"] or "").lower() not in tipos_fecha
    ]

    # ── Columnas temporales realmente detectadas en los datos ──
    cols_temporales, puntos, ultima_eval = {}, [], None
    df = None
    if dfs:
        from backend.rgenerator.reports.periodos import elegir_df_temporal
        tipos_columna = _tipos_columna(db, indicador["id_indicator"], org_id)
        df = elegir_df_temporal(dfs, tipos_columna)
        if df is not None and len(df):
            cols_temporales = detectar_columnas_temporales_df(df, tipos_columna)
            vistos = set()
            for _, row in df.iterrows():
                anio, mes, _ord = clave_temporal(row, cols_temporales)
                if anio and anio > 0:
                    vistos.add((anio, mes if mes and mes > 0 else 0))
            puntos = sorted(vistos)
        res = resolver_periodo_multi(dfs, {"tipo": "ultima_prueba"}, date.today(),
                                     _tipos_columna(db, indicador["id_indicator"], org_id))
        ultima_eval = res.to_dict()

    # ── Estado ──
    if total_filas == 0:
        estado, nota = BAD, "sin filas en metric_data"
    elif dims_fecha_sin_marcar:
        estado = WARN
        nota = (f"{total_filas} filas — dimensión de fecha SIN data_type='date': "
                + ", ".join(d["name"] for d in dims_fecha_sin_marcar))
    elif not (ultima_eval or {}).get("disponible"):
        estado = WARN
        nota = f"{total_filas} filas — no se pudo resolver la última evaluación"
    else:
        estado = OK
        nota = f"{total_filas} filas — última eval: {ultima_eval['descripcion']}"

    return {
        "metricas": metricas,
        "total_filas": total_filas,
        "ultima_created_at": ultima_carga.isoformat() if ultima_carga else None,
        "columnas_temporales": cols_temporales,
        "puntos_temporales": [list(p) for p in puntos],
        "rango_temporal": (
            {"desde": list(puntos[0]), "hasta": list(puntos[-1])} if puntos else None
        ),
        "ultima_evaluacion": ultima_eval,
        "dimensiones_fecha": {
            "marcadas_date": dims_fecha_marcadas,
            "parecen_fecha_sin_marcar": dims_fecha_sin_marcar,
            "usa_columna_fecha": bool(cols_temporales.get("fecha")),
        },
        "estado": estado,
        "nota": nota,
    }


def _tipos_columna(db, indicator_id: int, org_id: int) -> dict:
    """Reusa el helper del router para que el resolver vea los tipos de dimensión."""
    from backend.routers.indicators import _tipos_de_columna
    try:
        return _tipos_de_columna(db, indicator_id, org_id)
    except Exception:
        return {}


# =========================================================================
# 3. Dashboard
# =========================================================================

_TIPO_SPEC = {"configured_chart": "Gráficos", "configured_table": "Tablas"}
_RUTA_DATA = {"configured_chart": "/api/charts", "configured_table": "/api/tables"}


def _items_del_layout(layout: dict) -> list[dict]:
    items = []
    for tab in (layout.get("tabs") or []):
        for fila in (tab.get("rows") or []):
            for it in (fila.get("items") or []):
                if isinstance(it, dict):
                    items.append({**it, "_tab": tab.get("id") or tab.get("label")})
    return items


def dashboard_de_indicador(db, api: ApiClient, indicador: dict, resolver: bool) -> dict:
    from backend.models import Spec

    crudo = indicador["_raw_dashboard_layout"]
    layout = _json_seguro(crudo, {})
    if layout is None:
        return {
            "parsea": False, "n_tabs": 0, "n_items": 0, "referencias": [],
            "estado": BAD, "nota": "dashboard_layout no parsea como JSON",
        }
    if not layout:
        return {
            "parsea": True, "n_tabs": 0, "n_items": 0, "referencias": [],
            "estado": BAD, "nota": "dashboard_layout vacío",
        }

    items = _items_del_layout(layout)
    referencias, faltantes, vacios, errores = [], [], [], []

    for it in items:
        tipo = it.get("type")
        if tipo not in _TIPO_SPEC:
            continue
        spec_id = it.get("spec_id")
        ref = {
            "tab": it.get("_tab"),
            "type": tipo,
            "spec_id": spec_id,
            "title": it.get("title"),
            "existe": False,
            "tipo_spec_ok": False,
            "spec_name": None,
            "data": None,
        }
        spec = db.query(Spec).filter(
            Spec.id_spec == spec_id, Spec.org_id == indicador["org_id"]
        ).first() if spec_id else None
        if spec is not None:
            ref["existe"] = True
            ref["spec_name"] = spec.name
            ref["tipo_spec_ok"] = (spec.type == _TIPO_SPEC[tipo])
        if not ref["existe"] or not ref["tipo_spec_ok"]:
            faltantes.append(ref)

        if resolver and ref["existe"] and ref["tipo_spec_ok"]:
            ref["data"] = _resolver_item(api, tipo, spec_id)
            if ref["data"]["clase"] == "vacio":
                vacios.append(ref)
            elif ref["data"]["clase"] == "error":
                errores.append(ref)
        referencias.append(ref)

    n_ref = len(referencias)
    if faltantes:
        estado = BAD
        nota = (f"{len(items)} items — {len(faltantes)} referencia(s) rota(s): "
                + ", ".join(f"{f['type']}#{f['spec_id']}" for f in faltantes[:5]))
    elif errores:
        estado = BAD
        nota = (f"{len(items)} items — {len(errores)} con error al resolver: "
                + ", ".join(f"{e['type']}#{e['spec_id']}" for e in errores[:5]))
    elif vacios:
        estado = WARN
        nota = (f"{len(items)} items ({n_ref} refs OK) — {len(vacios)} sin datos: "
                + ", ".join(f"{v['type']}#{v['spec_id']}" for v in vacios[:5]))
    else:
        estado = OK
        nota = f"{len(items)} items, {n_ref} refs OK" + (" y con datos" if resolver else "")

    return {
        "parsea": True,
        "n_tabs": len(layout.get("tabs") or []),
        "n_items": len(items),
        "n_referencias": n_ref,
        "referencias": referencias,
        "estado": estado,
        "nota": nota,
    }


def _resolver_item(api: ApiClient, tipo: str, spec_id: int) -> dict:
    """Llama al endpoint de datos del chart/tabla y clasifica la respuesta."""
    ruta = f"{_RUTA_DATA[tipo]}/{spec_id}/data"
    t0 = time.time()
    try:
        r = api.get(ruta)
    except Exception as e:
        return {"status": None, "clase": "error", "detalle": f"{type(e).__name__}: {e}",
                "segundos": round(time.time() - t0, 1)}
    seg = round(time.time() - t0, 1)
    if r.status_code != 200:
        detalle = ""
        try:
            detalle = r.json().get("detail", "")
        except Exception:
            detalle = r.text[:200]
        return {"status": r.status_code, "clase": "error", "detalle": _corto(detalle, 200),
                "segundos": seg}
    try:
        payload = r.json()
    except Exception:
        return {"status": 200, "clase": "error", "detalle": "respuesta no-JSON", "segundos": seg}

    n = _contar_datos(payload)
    return {
        "status": 200,
        "clase": "ok" if n > 0 else "vacio",
        "n_filas": n,
        "segundos": seg,
    }


def _contar_datos(payload: Any) -> int:
    """Cuántas filas trae la respuesta de `/api/charts|tables/{id}/data`.

    Formas reales (ver `_render_chart_data`, `_render_table_data`,
    `_render_pivot_data`):
        charts → {"chart_type", "mapping", "aesthetics",
                  "dataset": {"x": [...], "series"|"y": [...]}, "n_rows"}
        tables → {"columns", "rows", "total_rows", "limit", "offset"}
        pivote → {"mode": "pivot", "pivot": {...}, "n_rows"}
    """
    if isinstance(payload, list):
        return len(payload)
    if not isinstance(payload, dict):
        return 0

    for clave in ("n_rows", "total_rows", "total"):
        v = payload.get(clave)
        if isinstance(v, int):
            return v

    ds = payload.get("dataset")
    if isinstance(ds, dict):
        x = ds.get("x")
        if isinstance(x, list) and x:
            return len(x)
        series = ds.get("series") or ds.get("y")
        if isinstance(series, list):
            if series and isinstance(series[0], dict):
                return sum(len(s.get("data") or s.get("values") or []) for s in series) or len(series)
            return len(series)
        for v in ds.values():
            if isinstance(v, list) and v:
                return len(v)
        return 0

    for clave in ("rows", "data", "values", "items", "records"):
        v = payload.get(clave)
        if isinstance(v, list):
            return len(v)
    return 0


# =========================================================================
# 4. Informes
# =========================================================================

def _pdf_paginas(contenido: bytes) -> tuple[Optional[int], Optional[str]]:
    try:
        import fitz
    except Exception as e:
        return None, f"PyMuPDF no disponible: {e}"
    try:
        doc = fitz.open(stream=contenido, filetype="pdf")
        n = doc.page_count
        doc.close()
        return n, None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _rango_personalizado(datos: dict) -> Optional[dict]:
    """`fecha_inicio`/`fecha_fin` (AAAA-MM) que SÍ tienen datos.

    Se acota al último año con datos para no cruzar el año (el resolver
    materializa el rango como listas por columna y un rango que cruza el
    año es un superconjunto — ver `periodos._resolver_personalizado`).
    """
    puntos = [tuple(p) for p in (datos.get("puntos_temporales") or [])]
    if not puntos:
        return None
    ultimo_anio = puntos[-1][0]
    del_anio = [p for p in puntos if p[0] == ultimo_anio]
    meses = [m for _, m in del_anio if m > 0]
    mes_ini = min(meses) if meses else 1
    mes_fin = max(meses) if meses else 12
    return {
        "fecha_inicio": f"{ultimo_anio:04d}-{mes_ini:02d}",
        "fecha_fin": f"{ultimo_anio:04d}-{mes_fin:02d}",
    }


def _resolver_local(db, indicador: dict, org_id: int, dfs: dict, periodo: dict) -> dict:
    """Qué dice el resolver de períodos del backend para este período.

    Es la referencia independiente contra la que se decide si un 400 es
    ESPERADO (el período de verdad no tiene datos) o SORPRESA.
    """
    from backend.rgenerator.reports.periodos import (
        aplicar_filtros_a_dataframes,
        resolver_periodo_multi,
    )
    if not dfs:
        return {"disponible": False, "motivo": "Sin datos cargados para este indicador."}
    try:
        base = dfs
        filtros = (periodo or {}).get("filtros") or {}
        if filtros:
            base = aplicar_filtros_a_dataframes(dfs, filtros)
        res = resolver_periodo_multi(
            base, periodo, date.today(),
            _tipos_columna(db, indicador["id_indicator"], org_id),
        )
        return res.to_dict()
    except Exception as e:
        return {"disponible": False, "motivo": f"excepción del resolver: {type(e).__name__}: {e}"}


def _clasificar(status: Optional[int], detalle: str, anticipado: bool,
                contenido: Optional[bytes], timeout: bool) -> tuple[str, str, Optional[int]]:
    """(clase, nota, paginas)."""
    if timeout:
        return "timeout", "el request excedió el timeout", None
    if status is None:
        return "error_red", detalle, None
    if status == 200:
        paginas, err = _pdf_paginas(contenido or b"")
        if paginas and paginas > 0:
            return "ok", f"{paginas} págs, {len(contenido or b'')//1024} KB", paginas
        return "ok_vacio", f"200 pero el PDF no es válido ({err or '0 páginas'})", paginas
    if status >= 500:
        return "500", detalle, None
    if status in (400, 404, 422):
        return ("400_esperado" if anticipado else "400_sorpresa"), detalle, None
    return "otro", f"HTTP {status}: {detalle}", None


def _detalle_error(r) -> str:
    try:
        return _corto(r.json().get("detail", r.text), 300)
    except Exception:
        return _corto(r.text, 300)


def informes_de_indicador(db, api: ApiClient, indicador: dict, org_id: int,
                          dfs: dict, datos: dict, out_dir: Path,
                          generar_pdfs: bool, asignatura_pref: Optional[str] = None) -> dict:
    """report-options + un intento de PDF por cada modo/informe disponible."""
    ind_id = indicador["id_indicator"]
    slug = _slug(indicador["name"])

    # ── report-options ──
    try:
        r = api.get(f"/api/indicators/{ind_id}/report-options")
        if r.status_code != 200:
            return {
                "report_options": {"status": r.status_code, "detalle": _detalle_error(r)},
                "modos": [], "especializados": [],
                "estado": BAD, "nota": f"report-options HTTP {r.status_code}",
            }
        opciones = r.json()
    except Exception as e:
        return {
            "report_options": {"status": None, "detalle": f"{type(e).__name__}: {e}"},
            "modos": [], "especializados": [],
            "estado": BAD, "nota": "report-options inaccesible",
        }

    cards = opciones.get("grupos", {}).get("periodo", [])
    especializados = opciones.get("grupos", {}).get("especializados", [])

    # ── Asignatura obligatoria (si los datos traen ≥2) ──
    descriptor = next((c.get("asignatura") for c in cards if c.get("asignatura")), None)
    asignatura_dim = descriptor.get("dimension") if descriptor else None
    valores_asig = (descriptor.get("valores") or []) if descriptor else []
    # Por defecto la PRIMERA disponible; `--asignatura` permite fijar otra
    # cuando la primera es marginal (ej. HISTORIA en SIMCE Panguipulli).
    asignatura_val = None
    if valores_asig:
        asignatura_val = next(
            (v for v in valores_asig
             if asignatura_pref and _slug(v) == _slug(asignatura_pref)),
            valores_asig[0],
        )
    filtros_asig = {asignatura_dim: [asignatura_val]} if asignatura_dim and asignatura_val else {}

    rango = _rango_personalizado(datos)
    resultados = []

    for card in cards:
        tipo = card["periodo"]["tipo"]
        periodo: dict[str, Any] = {"tipo": tipo}
        if filtros_asig:
            periodo["filtros"] = dict(filtros_asig)
        if tipo == "personalizado":
            if not rango:
                resultados.append({
                    "modo": tipo, "card_disponible": card["disponible"],
                    "clase": "omitido",
                    "nota": "no hay puntos temporales para construir un rango con datos",
                })
                continue
            periodo.update(rango)

        local = _resolver_local(db, indicador, org_id, dfs, periodo)
        anticipado = (not card["disponible"]) or (not local.get("disponible"))

        body = {"tipo": "evaluacion", "periodo": periodo}
        if filtros_asig:
            body["filters"] = dict(filtros_asig)

        nombre_archivo = f"{slug}_{tipo}"
        if asignatura_val:
            nombre_archivo += f"_{_slug(asignatura_val)}"

        res = _intentar_pdf(
            api, f"/api/indicators/{ind_id}/export-pdf", body,
            out_dir / f"{nombre_archivo}.pdf", anticipado, generar_pdfs,
        )
        res.update({
            "modo": tipo,
            "endpoint": f"POST /api/indicators/{ind_id}/export-pdf",
            "card_disponible": card["disponible"],
            "card_motivo": card["motivo_no_disponible"],
            "card_motor": card.get("motor"),
            "tipo_layout": card.get("tipo_layout"),
            "asignatura": asignatura_val,
            "periodo_enviado": periodo,
            "resolver_local": local,
        })
        resultados.append(res)

    # ── Sonda extra: el frontend manda engine='weasyprint' aun con `periodo`,
    #    lo que DESACTIVA el motor único (indicators.py: `if modo_periodo and
    #    not engine_override`). Se prueba para dejar constancia de la
    #    divergencia entre lo que anuncia report-options y lo que la UI pide.
    if any(str(c.get("motor", "")).startswith("custom:") for c in cards):
        card_ref = next((c for c in cards if c["periodo"]["tipo"] == "ultima_prueba"), None)
        if card_ref is not None:
            periodo = {"tipo": "ultima_prueba"}
            if filtros_asig:
                periodo["filtros"] = dict(filtros_asig)
            local = _resolver_local(db, indicador, org_id, dfs, periodo)
            body = {"tipo": "evaluacion", "engine": "weasyprint", "periodo": periodo}
            if filtros_asig:
                body["filters"] = dict(filtros_asig)
            nombre = f"{slug}_ultima_prueba_engine_weasyprint"
            if asignatura_val:
                nombre += f"_{_slug(asignatura_val)}"
            res = _intentar_pdf(
                api, f"/api/indicators/{ind_id}/export-pdf", body,
                out_dir / f"{nombre}.pdf",
                (not card_ref["disponible"]) or (not local.get("disponible")),
                generar_pdfs,
            )
            res.update({
                "modo": "ultima_prueba (engine=weasyprint, como lo manda la UI)",
                "endpoint": f"POST /api/indicators/{ind_id}/export-pdf",
                "card_disponible": card_ref["disponible"],
                "card_motor": card_ref.get("motor"),
                "sonda": "frontend_engine_override",
            })
            resultados.append(res)

    # ── Informes especializados (registro reports/custom/) ──
    res_esp = []
    filtros_base = {}
    ult = (datos.get("ultima_evaluacion") or {})
    if ult.get("disponible"):
        filtros_base.update(ult.get("filtros") or {})
    filtros_base.update(filtros_asig)

    for inf in especializados:
        nombre = inf.get("nombre")
        if inf.get("formato") != "pdf":
            res_esp.append({
                "nombre": nombre, "clase": "omitido",
                "nota": f"formato '{inf.get('formato')}' — fuera del alcance de esta matriz",
            })
            continue
        body = {"indicator_id": ind_id, "filtros": filtros_base}
        destino = out_dir / (
            f"{slug}_custom_{_slug(nombre)}"
            + (f"_{_slug(asignatura_val)}" if asignatura_val else "")
            + ".pdf"
        )
        res = _intentar_pdf(
            api, f"/api/reports/custom/{nombre}", body, destino,
            anticipado=not ult.get("disponible"), generar=generar_pdfs,
        )
        res.update({
            "nombre": nombre,
            "label": inf.get("label"),
            "endpoint": f"POST /api/reports/custom/{nombre}",
            "requiere_filtro_temporal": inf.get("requiere_filtro_temporal"),
            "filtros_enviados": filtros_base,
        })
        res_esp.append(res)

    todos = resultados + res_esp
    n_ok = sum(1 for r in todos if r.get("clase") == "ok")
    n_sorpresa = sum(1 for r in todos if r.get("clase") in ("400_sorpresa", "500", "error_red",
                                                            "timeout", "ok_vacio", "otro"))
    n_esperado = sum(1 for r in todos if r.get("clase") == "400_esperado")
    if n_sorpresa:
        estado = BAD
    elif n_ok == 0:
        estado = BAD
    elif n_esperado:
        estado = WARN
    else:
        estado = OK
    nota = f"{n_ok} OK / {n_esperado} 400-esperado / {n_sorpresa} problema(s)"

    return {
        "engine_type": opciones.get("engine_type"),
        "engine_type_origen": opciones.get("engine_type_origen"),
        "asignatura_requerida": descriptor,
        "rango_personalizado": rango,
        "modos": resultados,
        "especializados": res_esp,
        "estado": estado,
        "nota": nota,
    }


def _intentar_pdf(api: ApiClient, ruta: str, body: dict, destino: Path,
                  anticipado: bool, generar: bool) -> dict:
    if not generar:
        return {"clase": "omitido", "nota": "--sin-pdf", "status": None}

    t0 = time.time()
    timeout = False
    status: Optional[int] = None
    contenido: Optional[bytes] = None
    detalle = ""
    try:
        r = api.post(ruta, json=body)
        status = r.status_code
        if status == 200:
            contenido = r.content
        else:
            detalle = _detalle_error(r)
    except Exception as e:
        if "timeout" in type(e).__name__.lower() or "Timeout" in str(type(e)):
            timeout = True
        detalle = f"{type(e).__name__}: {e}"
    seg = round(time.time() - t0, 1)

    clase, nota, paginas = _clasificar(status, detalle, anticipado, contenido, timeout)

    archivo = None
    if clase in ("ok", "ok_vacio") and contenido:
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(contenido)
        archivo = str(destino)

    return {
        "status": status,
        "clase": clase,
        "nota": nota,
        "detalle": detalle or None,
        "paginas": paginas,
        "bytes": len(contenido) if contenido else 0,
        "segundos": seg,
        "archivo": archivo,
        "anticipado": anticipado,
        "body": body,
    }


# =========================================================================
# Markdown
# =========================================================================

_ICONO_CLASE = {
    "ok": OK,
    "ok_vacio": BAD,
    "400_esperado": WARN,
    "400_sorpresa": BAD,
    "500": BAD,
    "timeout": BAD,
    "error_red": BAD,
    "otro": BAD,
    "omitido": NA,
}

_MODOS_TABLA = ["ultima_prueba", "semestral", "anual", "personalizado"]
_TITULO_MODO = {
    "ultima_prueba": "Última prueba",
    "semestral": "Semestral",
    "anual": "Anual",
    "personalizado": "Personalizado",
}


def _celda_modo(res: Optional[dict]) -> str:
    if res is None:
        return NA
    icono = _ICONO_CLASE.get(res.get("clase"), "?")
    return f"{icono} {_celda_md(res.get('nota'))}"


def render_markdown(reporte: dict) -> str:
    L: list[str] = []
    meta = reporte["meta"]
    L.append(f"# QA — Matriz de indicadores (org {meta['org_id']})")
    L.append("")
    L.append(f"- **Fecha de ejecución**: {meta['ejecutado_en']}")
    L.append(f"- **API**: `{meta['base_url']}`  ·  **Usuario QA**: `{meta['usuario']}`")
    L.append(f"- **Salida**: `{meta['out_dir']}`")
    L.append(f"- **Indicadores revisados**: {len(reporte['indicadores'])}")
    L.append("")
    L.append("Leyenda: ✅ correcto · ⚠️ revisar (400 coherente con la cobertura de "
             "datos, o aviso menor) · ❌ falla · — no aplica.")
    L.append("")

    # ── Tabla resumen ──
    L.append("## Tabla-resumen")
    L.append("")
    cab = ["Indicador", "ETL", "Datos + última carga", "Dashboard"]
    cab += [_TITULO_MODO[m] for m in _MODOS_TABLA]
    cab += ["Informe especializado"]
    L.append("| " + " | ".join(cab) + " |")
    L.append("|" + "---|" * len(cab))

    for ind in reporte["indicadores"]:
        etl = ind["etl"]
        datos = ind["datos"]
        dash = ind["dashboard"]
        inf = ind["informes"]

        por_modo = {r.get("modo"): r for r in inf.get("modos", []) if not r.get("sonda")}
        celdas = [
            f"**{ind['name']}** (id {ind['id_indicator']})",
            f"{etl['estado']} {_celda_md(etl['nota'])}",
            f"{datos['estado']} {_celda_md(datos['nota'])}",
            f"{dash['estado']} {_celda_md(dash['nota'])}",
        ]
        for m in _MODOS_TABLA:
            celdas.append(_celda_modo(por_modo.get(m)))

        esp = inf.get("especializados", [])
        if not esp:
            celdas.append(NA)
        else:
            partes = []
            for e in esp:
                icono = _ICONO_CLASE.get(e.get("clase"), "?")
                partes.append(f"{icono} `{e.get('nombre')}`: {_celda_md(e.get('nota'))}")
            celdas.append("<br>".join(partes))
        L.append("| " + " | ".join(celdas) + " |")
    L.append("")

    # ── Hallazgos ──
    L.append("## Hallazgos")
    L.append("")
    if reporte["hallazgos"]:
        for h in reporte["hallazgos"]:
            L.append(f"- **[{h['severidad']}] {h['indicador']}** — {h['titulo']}: {h['detalle']}")
    else:
        L.append("- Sin hallazgos.")
    L.append("")

    # ── Detalle por indicador ──
    L.append("## Detalle por indicador")
    L.append("")
    for ind in reporte["indicadores"]:
        L.append(f"### {ind['id_indicator']} — {ind['name']}")
        L.append("")
        L.append(f"- `report_engine_type`: `{ind['report_engine_type'] or 'null'}` · "
                 f"resuelto por la API: `{ind['informes'].get('engine_type')}` "
                 f"(origen `{ind['informes'].get('engine_type_origen')}`)")
        L.append(f"- Métricas: " + ", ".join(
            f"`{m['name']}` (id {m['id_metric']}, {m.get('filas_metric_data', 0)} filas)"
            for m in ind["datos"]["metricas"]) or "- Métricas: (ninguna)")
        rango = ind["datos"].get("rango_temporal")
        if rango:
            L.append(f"- Cobertura temporal detectada: {rango['desde'][0]}-{rango['desde'][1]:02d} "
                     f"→ {rango['hasta'][0]}-{rango['hasta'][1]:02d} "
                     f"({len(ind['datos']['puntos_temporales'])} puntos)")
        L.append(f"- Última fila cargada (`created_at`): "
                 f"{ind['datos'].get('ultima_created_at') or 'n/d'}")
        cols = ind["datos"].get("columnas_temporales") or {}
        if cols:
            L.append("- Columnas temporales detectadas: " + ", ".join(
                f"{k}=`{v}`" for k, v in cols.items() if v) or "(ninguna)")
        dfec = ind["datos"]["dimensiones_fecha"]
        if dfec["marcadas_date"]:
            L.append("- Dimensiones con `data_type='date'`: " + ", ".join(
                f"`{d['name']}`" for d in dfec["marcadas_date"]))
        if dfec["parecen_fecha_sin_marcar"]:
            L.append("- ⚠️ Parecen fecha pero NO están marcadas: " + ", ".join(
                f"`{d['name']}` (`{d['data_type']}`)" for d in dfec["parecen_fecha_sin_marcar"]))
        L.append("")

        L.append("**ETL** — " + ind["etl"]["criterio_asociacion"])
        L.append("")
        if ind["etl"]["pipelines"]:
            L.append("| Pipeline | Match | config_json | Steps | last_run |")
            L.append("|---|---|---|---|---|")
            for p in ind["etl"]["pipelines"]:
                L.append(f"| #{p['pipeline_id']} {_celda_md(p['nombre'])} | {p['match']} | "
                         f"{'OK' if p['config_json_parsea'] else 'NO PARSEA'} | {p['n_steps']} | "
                         f"{p['last_run'] or '—'} |")
        else:
            L.append("_Sin pipelines asociados._")
        L.append("")

        L.append(f"**Dashboard** — {ind['dashboard']['nota']}")
        L.append("")
        refs = ind["dashboard"].get("referencias") or []
        problem = [r for r in refs if (not r["existe"]) or (not r["tipo_spec_ok"])
                   or (r.get("data") or {}).get("clase") in ("vacio", "error")]
        if problem:
            L.append("| Tab | Tipo | spec_id | Título | Problema |")
            L.append("|---|---|---|---|---|")
            for r in problem:
                if not r["existe"]:
                    pb = "spec inexistente"
                elif not r["tipo_spec_ok"]:
                    pb = "spec de tipo incorrecto"
                else:
                    d = r["data"]
                    pb = ("sin datos" if d["clase"] == "vacio"
                          else f"HTTP {d.get('status')}: {_celda_md(d.get('detalle'))}")
                L.append(f"| {_celda_md(r['tab'])} | {r['type']} | {r['spec_id']} | "
                         f"{_celda_md(r['title'])} | {pb} |")
        else:
            L.append("_Todas las referencias existen y devuelven datos._")
        L.append("")

        L.append("**Informes**")
        L.append("")
        L.append("| Informe | Card disponible | HTTP | Clase | Detalle | Archivo |")
        L.append("|---|---|---|---|---|---|")
        for r in ind["informes"].get("modos", []) + ind["informes"].get("especializados", []):
            etiqueta = r.get("modo") or f"custom:{r.get('nombre')}"
            disp = r.get("card_disponible")
            disp_txt = "—" if disp is None else ("sí" if disp else f"NO ({_celda_md(r.get('card_motivo'))})")
            arch = Path(r["archivo"]).name if r.get("archivo") else "—"
            L.append(f"| {_celda_md(etiqueta)} | {disp_txt} | {r.get('status') or '—'} | "
                     f"{_ICONO_CLASE.get(r.get('clase'), '?')} {r.get('clase')} | "
                     f"{_celda_md(r.get('detalle') or r.get('nota'))} | {arch} |")
        L.append("")

    # ── Inventario de PDFs ──
    L.append("## PDFs generados")
    L.append("")
    if reporte["pdfs"]:
        L.append("| Archivo | Páginas | Tamaño |")
        L.append("|---|---|---|")
        for p in reporte["pdfs"]:
            L.append(f"| `{p['archivo']}` | {p['paginas']} | {p['kb']} KB |")
    else:
        L.append("_Ninguno._")
    L.append("")

    # ── Pipelines huérfanos ──
    L.append("## Pipelines sin indicador asociado")
    L.append("")
    if reporte["pipelines_huerfanos"]:
        L.append("| Pipeline | metric_ids | Steps | last_run |")
        L.append("|---|---|---|---|")
        for p in reporte["pipelines_huerfanos"]:
            L.append(f"| #{p['pipeline_id']} {_celda_md(p['nombre'])} | "
                     f"{p['metric_ids'] or '—'} | {p['n_steps']} | {p['last_run'] or '—'} |")
    else:
        L.append("_Ninguno._")
    L.append("")
    return "\n".join(L)


# =========================================================================
# Hallazgos
# =========================================================================

def recolectar_hallazgos(indicadores: list[dict], huerfanos: list[dict]) -> list[dict]:
    out = []
    for ind in indicadores:
        nom = f"{ind['id_indicator']} {ind['name']}"
        etl = ind["etl"]
        if etl["criterio_asociacion"] == "sin asociación clara":
            out.append({"severidad": "ETL", "indicador": nom, "titulo": "sin asociación clara",
                        "detalle": "ningún pipeline referencia sus métricas ni coincide por nombre"})
        elif "DÉBIL" in etl["criterio_asociacion"]:
            out.append({"severidad": "ETL", "indicador": nom, "titulo": "asociación ambigua",
                        "detalle": etl["nota"]})
        for p in etl["pipelines"]:
            if not p["config_json_parsea"]:
                out.append({"severidad": "ETL", "indicador": nom,
                            "titulo": f"config_json roto en pipeline #{p['pipeline_id']}",
                            "detalle": p["config_json_error"] or ""})
            if p.get("nombre_divergente"):
                out.append({"severidad": "ETL", "indicador": nom,
                            "titulo": f"nombre divergente con el pipeline #{p['pipeline_id']}",
                            "detalle": (f"'{p['nombre']}' escribe las métricas "
                                        f"{p['metricas_comunes']} de este indicador, pero su "
                                        "nombre no lo sugiere: la relación solo es visible "
                                        "leyendo el config_json")})
            if p.get("metricas_no_consumidas"):
                out.append({"severidad": "ETL", "indicador": nom,
                            "titulo": f"pipeline #{p['pipeline_id']} escribe métricas que este "
                                      "indicador no consume",
                            "detalle": f"metric_ids {p['metricas_no_consumidas']}"})

        dfec = ind["datos"]["dimensiones_fecha"]
        for d in dfec["parecen_fecha_sin_marcar"]:
            out.append({"severidad": "DATOS", "indicador": nom,
                        "titulo": f"dimensión '{d['name']}' parece fecha y no está marcada",
                        "detalle": f"data_type='{d['data_type']}' — debería ser 'date' para que "
                                   "los informes semestral/anual puedan derivar año y mes"})
        if ind["datos"]["total_filas"] == 0:
            out.append({"severidad": "DATOS", "indicador": nom, "titulo": "sin datos",
                        "detalle": "0 filas en metric_data"})

        dash = ind["dashboard"]
        if not dash.get("parsea"):
            out.append({"severidad": "DASHBOARD", "indicador": nom,
                        "titulo": "dashboard_layout no parsea", "detalle": dash["nota"]})
        for r in dash.get("referencias") or []:
            if not r["existe"]:
                out.append({"severidad": "DASHBOARD", "indicador": nom,
                            "titulo": f"referencia rota {r['type']}#{r['spec_id']}",
                            "detalle": f"tab '{r['tab']}', título '{r['title']}'"})
            elif not r["tipo_spec_ok"]:
                out.append({"severidad": "DASHBOARD", "indicador": nom,
                            "titulo": f"spec de tipo incorrecto {r['type']}#{r['spec_id']}",
                            "detalle": f"spec '{r['spec_name']}'"})
            else:
                d = r.get("data") or {}
                if d.get("clase") == "vacio":
                    out.append({"severidad": "DASHBOARD", "indicador": nom,
                                "titulo": f"{r['type']}#{r['spec_id']} sin datos",
                                "detalle": f"'{r['title']}' (tab {r['tab']}) resuelve 200 con 0 filas"})
                elif d.get("clase") == "error":
                    out.append({"severidad": "DASHBOARD", "indicador": nom,
                                "titulo": f"{r['type']}#{r['spec_id']} error al resolver",
                                "detalle": f"HTTP {d.get('status')}: {d.get('detalle')}"})

        for r in ind["informes"].get("modos", []) + ind["informes"].get("especializados", []):
            clase = r.get("clase")
            etiqueta = r.get("modo") or f"custom:{r.get('nombre')}"
            if clase in ("400_sorpresa", "500", "timeout", "error_red", "ok_vacio", "otro"):
                out.append({"severidad": "INFORME", "indicador": nom,
                            "titulo": f"{etiqueta} → {clase}",
                            "detalle": _corto(r.get("detalle") or r.get("nota"), 300)})
            # Card apagada por CONFIGURACIÓN (no por falta de datos): es un
            # pendiente accionable, no una consecuencia de la cobertura.
            motivo = r.get("card_motivo") or ""
            if r.get("card_disponible") is False and "Editor de Layout" in motivo:
                out.append({"severidad": "CONFIG", "indicador": nom,
                            "titulo": f"card '{etiqueta}' deshabilitada por falta de pdf_layout",
                            "detalle": _corto(motivo, 220)})

        # Divergencia motor único vs. lo que manda la UI (`engine=weasyprint`).
        sonda = next((r for r in ind["informes"].get("modos", [])
                      if r.get("sonda") == "frontend_engine_override"), None)
        canonico = next((r for r in ind["informes"].get("modos", [])
                         if r.get("modo") == "ultima_prueba"), None)
        if sonda and canonico and sonda.get("clase") == "ok" and canonico.get("clase") == "ok":
            if (sonda.get("paginas") or 0) != (canonico.get("paginas") or 0):
                out.append({
                    "severidad": "INFORME", "indicador": nom,
                    "titulo": "el `engine` explícito de la UI desactiva el motor único",
                    "detalle": (
                        f"report-options anuncia motor '{canonico.get('card_motor')}', pero el "
                        f"mismo período con engine='weasyprint' (lo que manda Results.jsx / "
                        f"GenerateReportModal.jsx) devuelve {sonda.get('paginas')} págs en vez de "
                        f"{canonico.get('paginas')}: en indicators.py el módulo del motor único "
                        "solo se resuelve `if modo_periodo and not engine_override`"),
                })
    for p in huerfanos:
        out.append({"severidad": "ETL", "indicador": "(ninguno)",
                    "titulo": f"pipeline #{p['pipeline_id']} '{p['nombre']}' sin indicador",
                    "detalle": f"metric_ids={p['metric_ids']}, steps={p['n_steps']}"})
    return out


# =========================================================================
# Main
# =========================================================================

def main() -> int:
    hoy = date.today().isoformat()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--org", type=int, default=1, help="id de la organización (default 1)")
    ap.add_argument("--base-url", default="http://localhost:8001",
                    help="URL base de la API (default http://localhost:8001)")
    ap.add_argument("--out", default=None,
                    help=f"directorio de salida (default data/output/qa_indicadores/{hoy}/)")
    ap.add_argument("--md-out", default=None,
                    help=f"markdown (default docs/reportes/qa_matriz_indicadores_{hoy}.md)")
    ap.add_argument("--email", default="qa.admin@rgenerator.local")
    ap.add_argument("--password", default="qaadmin1234")
    ap.add_argument("--crear-usuario", action="store_true",
                    help="crea (o resetea) el usuario QA antes de autenticarse")
    ap.add_argument("--database-url", default=None,
                    help="override de DATABASE_URL (por defecto usa el del entorno)")
    ap.add_argument("--timeout", type=int, default=600,
                    help="timeout por request en segundos (default 600)")
    ap.add_argument("--indicadores", default=None,
                    help="lista de ids separada por comas (default: todos los de la org)")
    ap.add_argument("--sin-pdf", action="store_true",
                    help="no genera PDFs (solo ETL/datos/dashboard/report-options)")
    ap.add_argument("--sin-dashboard-data", action="store_true",
                    help="no resuelve charts/tablas del dashboard vía API")
    ap.add_argument("--asignatura", default=None,
                    help="asignatura a usar cuando el indicador exige elegir una "
                         "(default: la primera que ofrece report-options)")
    args = ap.parse_args()

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    out_dir = Path(args.out) if args.out else _REPO_ROOT / "data" / "output" / "qa_indicadores" / hoy
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    md_out = Path(args.md_out) if args.md_out else _REPO_ROOT / "docs" / "reportes" / f"qa_matriz_indicadores_{hoy}.md"
    md_out.parent.mkdir(parents=True, exist_ok=True)

    from backend.database import SessionLocal
    from backend.models import Indicator, IndicatorMetric

    db = SessionLocal()
    try:
        if args.crear_usuario:
            _asegurar_usuario_qa(db, args.org, args.email, args.password)

        api = ApiClient(args.base_url, args.timeout)
        usuario = api.login(args.email, args.password)
        if usuario["org_id"] != args.org:
            print(f"[!] El usuario {args.email} pertenece a la org {usuario['org_id']}, "
                  f"no a la {args.org}. Abortando.", file=sys.stderr)
            return 2
        print(f"[i] Autenticado como {usuario['email']} (org {usuario['org_id']} — {usuario['org_name']})")

        pipelines = analizar_pipelines(db, args.org)
        print(f"[i] {len(pipelines)} pipelines en la org {args.org}")

        q = db.query(Indicator).filter(Indicator.org_id == args.org)
        if args.indicadores:
            ids = [int(x) for x in args.indicadores.split(",") if x.strip()]
            q = q.filter(Indicator.id_indicator.in_(ids))
        registros = q.order_by(Indicator.id_indicator).all()

        indicadores: list[dict] = []
        metric_ids_usados: set[int] = set()

        for rec in registros:
            metric_ids = [l.id_metric for l in db.query(IndicatorMetric).filter(
                IndicatorMetric.id_indicator == rec.id_indicator).all()]
            metric_ids_usados.update(metric_ids)
            ind = {
                "id_indicator": rec.id_indicator,
                "name": rec.name,
                "org_id": rec.org_id,
                "type": rec.type,
                "report_engine_type": rec.report_engine_type,
                "metric_ids": sorted(metric_ids),
                "_raw_dashboard_layout": rec.dashboard_layout,
                "pdf_layout_tiene_sections": bool(
                    (_json_seguro(rec.pdf_layout, {}) or {}).get("sections")),
                "pdf_layout_historico_tiene_sections": bool(
                    (_json_seguro(rec.pdf_layout_historico, {}) or {}).get("sections")),
            }
            print(f"\n[>] Indicador {ind['id_indicator']} — {ind['name']}")

            # dataframes (una sola carga, compartida por datos + informes)
            dfs: dict = {}
            try:
                from backend.rgenerator.reports.data import cargar_dataframes_indicator
                dfs = cargar_dataframes_indicator(
                    db, indicator_id=ind["id_indicator"], org_id=args.org, filtros={}
                ) or {}
            except Exception as e:
                print(f"    [!] no se pudieron cargar los dataframes: {type(e).__name__}: {e}")

            ind["etl"] = etl_de_indicador(ind, pipelines)
            print(f"    ETL       {ind['etl']['estado']} {ind['etl']['nota']}")

            ind["datos"] = datos_de_indicador(db, ind, args.org, dfs)
            print(f"    DATOS     {ind['datos']['estado']} {ind['datos']['nota']}")

            ind["dashboard"] = dashboard_de_indicador(
                db, api, ind, resolver=not args.sin_dashboard_data)
            print(f"    DASHBOARD {ind['dashboard']['estado']} {ind['dashboard']['nota']}")

            ind["informes"] = informes_de_indicador(
                db, api, ind, args.org, dfs, ind["datos"], out_dir,
                generar_pdfs=not args.sin_pdf, asignatura_pref=args.asignatura)
            print(f"    INFORMES  {ind['informes']['estado']} {ind['informes']['nota']}")
            for r in ind["informes"]["modos"] + ind["informes"]["especializados"]:
                etiqueta = r.get("modo") or f"custom:{r.get('nombre')}"
                print(f"        - {etiqueta:52s} {r.get('clase'):14s} "
                      f"{_corto(r.get('detalle') or r.get('nota'), 90)}")

            ind.pop("_raw_dashboard_layout", None)
            indicadores.append(ind)

        huerfanos = [
            {k: p[k] for k in ("pipeline_id", "nombre", "metric_ids", "n_steps", "last_run")}
            for p in pipelines
            if not (set(p["metric_ids"]) & metric_ids_usados)
        ]

        pdfs = []
        for ind in indicadores:
            for r in ind["informes"]["modos"] + ind["informes"]["especializados"]:
                if r.get("archivo"):
                    pdfs.append({
                        "archivo": Path(r["archivo"]).name,
                        "paginas": r.get("paginas"),
                        "kb": round((r.get("bytes") or 0) / 1024, 1),
                        "indicador": ind["name"],
                        "modo": r.get("modo") or f"custom:{r.get('nombre')}",
                    })

        reporte = {
            "meta": {
                "org_id": args.org,
                "base_url": args.base_url,
                "usuario": args.email,
                "ejecutado_en": datetime.now().isoformat(timespec="seconds"),
                "out_dir": str(out_dir),
                "md_out": str(md_out),
                "timeout_s": args.timeout,
                "pdfs_generados": not args.sin_pdf,
            },
            "pipelines": [
                {k: v for k, v in p.items() if k != "tokens"} for p in pipelines
            ],
            "pipelines_huerfanos": huerfanos,
            "indicadores": indicadores,
            "pdfs": pdfs,
        }
        reporte["hallazgos"] = recolectar_hallazgos(indicadores, huerfanos)

        (out_dir / "matriz.json").write_text(
            json.dumps(reporte, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        md = render_markdown(reporte)
        md_out.write_text(md, encoding="utf-8")
        (out_dir / md_out.name).write_text(md, encoding="utf-8")

        print(f"\n[✓] JSON     → {out_dir / 'matriz.json'}")
        print(f"[✓] Markdown → {md_out}")
        print(f"[✓] PDFs     → {out_dir} ({len(pdfs)} archivos)")
        print(f"[i] Hallazgos: {len(reporte['hallazgos'])}")
        return 0
    finally:
        db.close()


def _asegurar_usuario_qa(db, org_id: int, email: str, password: str) -> None:
    """Crea o resetea el usuario admin de QA (idempotente)."""
    from backend.auth import hash_password
    from backend.models import User

    u = db.query(User).filter(User.email == email).first()
    if u is None:
        u = User(name="QA Admin", email=email, password_hash=hash_password(password),
                 org_id=org_id, role="admin", is_active=True, is_superadmin=False)
        db.add(u)
        db.commit()
        print(f"[i] usuario QA creado: {email} (id {u.id})")
    else:
        u.password_hash = hash_password(password)
        u.org_id = org_id
        u.role = "admin"
        u.is_active = True
        db.commit()
        print(f"[i] usuario QA actualizado: {email} (id {u.id})")


if __name__ == "__main__":
    sys.exit(main())
