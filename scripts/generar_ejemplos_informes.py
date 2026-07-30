"""Genera un ejemplo de CADA informe disponible de CADA indicador.

Herramienta de QA (guion g4 de docs/qa/manual/): recorre todos los
indicadores de la org, consulta /report-options y genera cada opción
disponible, guardando los archivos en data/tmp/ejemplos_informes/ con
nombres claros. Imprime una tabla resumen OK/ERROR al final.

Uso (dentro del contenedor backend, contra la DB canónica):
    docker compose -f docker-compose.dev.yml exec backend \
        python scripts/generar_ejemplos_informes.py

Elección de filtros: para informes v2 (que exigen UN punto temporal) se
escanean los datos del indicador y se elige automáticamente el primer
valor disponible del filtro temporal requerido (Hito+Año para DIA).
El resto de informes se genera sin filtros (dataset completo).
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import requests

BASE = "http://localhost:8000"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "tmp" / "ejemplos_informes"

# Preferencias al elegir el punto temporal (si existen en los datos)
PREFERENCIA_HITO = ["INTERMEDIO", "DIAGNOSTICO", "CIERRE"]


def _slug(text: str) -> str:
    s = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def _token() -> str:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from backend.auth import create_access_token
    return create_access_token(1, 1, "admin")


def _datos_indicador(hdr: dict, indicator_id: int) -> tuple[dict[str, list], list[dict]]:
    """(valores_por_dimension, filas) del indicador.

    `dimensions` es un dict {id_str: {id, name, data_type, values}}; `data`
    es {id_metric: [{dimensions_json: {id_dim: valor}}]}. Las filas se
    devuelven ya traducidas a {nombre_dimension: valor} para poder validar
    COMBINACIONES de filtros (ej Hito+Año) y no solo valores sueltos.
    """
    r = requests.get(f"{BASE}/api/results/indicator/{indicator_id}/data", headers=hdr, timeout=180)
    r.raise_for_status()
    payload = r.json()
    dims = payload.get("dimensions") or {}
    valores = {meta["name"]: [str(v) for v in meta.get("values") or []] for meta in dims.values()}
    nombre_por_id = {str(k): meta["name"] for k, meta in dims.items()}

    filas: list[dict] = []
    for registros in (payload.get("data") or {}).values():
        for reg in registros:
            filas.append({
                nombre_por_id[k]: str(v)
                for k, v in (reg.get("dimensions_json") or {}).items()
                if k in nombre_por_id
            })
    return valores, filas


def _filtro_temporal(
    requeridos: list[str],
    valores: dict[str, list],
    filas: list[dict] | None = None,
) -> dict | None:
    """Elige UN punto temporal que EXISTA en los datos. None si no hay.

    Con `filas` se valida la combinación completa (Hito+Año): elegir Hito y
    Año por separado producía combos vacíos (ej INTERMEDIO+2026 cuando
    INTERMEDIO solo existe en 2025) y el informe salía en blanco.
    """
    filtros = {}
    if "Hito" in requeridos:
        # DIA: Hito + Año — preferir el año más reciente y, dentro de él, el
        # hito más avanzado que tenga datos.
        anios = valores.get("Año", [])
        combos = {
            (f.get("Hito"), f.get("Año"))
            for f in (filas or [])
            if f.get("Hito") and f.get("Año")
        }
        if combos:
            for anio in sorted({a for _, a in combos}, reverse=True):
                hitos = {h for h, a in combos if a == anio}
                elegido = next((h for h in PREFERENCIA_HITO if h in hitos), None)
                if elegido:
                    return {"Hito": elegido, "Año": anio}
        hitos = valores.get("Hito", [])
        if not hitos:
            return None
        filtros["Hito"] = next((h for h in PREFERENCIA_HITO if h in hitos), hitos[0])
        if anios:
            filtros["Año"] = max(anios)
        return filtros
    for campo in requeridos:  # SIMCE: Mes | N Prueba | Numero_Prueba
        vals = valores.get(campo, [])
        if vals:
            filtros[campo] = vals[0]
            return filtros
    return None


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    hdr = {"Authorization": f"Bearer {_token()}"}
    indicators = requests.get(f"{BASE}/api/indicators/", headers=hdr, timeout=60).json()

    resumen: list[tuple[str, str, str]] = []  # (archivo, estado, detalle)
    for ind in indicators:
        iid, nombre = ind["id_indicator"], ind["name"]
        opciones = requests.get(
            f"{BASE}/api/indicators/{iid}/report-options", headers=hdr, timeout=60
        ).json()["opciones"]
        valores = filas = None  # lazy: solo escanear datos si alguna opción lo necesita

        for op in opciones:
            archivo = f"{_slug(nombre)}__{_slug(op['id'])}.{'docx' if op['formato'] == 'word' else 'pdf'}"
            if not op["disponible"]:
                resumen.append((archivo, "OMITIDO", op.get("motivo_no_disponible") or "no disponible"))
                continue
            if op.get("requiere_configuracion"):
                resumen.append((archivo, "OMITIDO", "requiere configuración manual (rango/filtros)"))
                continue
            try:
                if op["motor"] == "custom":
                    # Informe hardcodeado del registro reports/custom/.
                    filtros = {}
                    requeridos = op.get("requiere_filtro_temporal") or []
                    if requeridos:
                        if valores is None:
                            valores, filas = _datos_indicador(hdr, iid)
                        filtros = _filtro_temporal(requeridos, valores, filas) or {}
                        if not filtros:
                            resumen.append((archivo, "OMITIDO", "sin valores temporales en los datos"))
                            continue
                    resp = requests.post(
                        f"{BASE}/api/reports/custom/{op['nombre']}", headers=hdr, timeout=300,
                        json={"indicator_id": iid, "filtros": filtros},
                    )
                elif op["motor"] == "v2":  # contrato legacy (pre-registro custom)
                    if valores is None:
                        valores, filas = _datos_indicador(hdr, iid)
                    filtros = _filtro_temporal(
                        op.get("requiere_filtro_temporal", []), valores, filas
                    )
                    if filtros is None:
                        resumen.append((archivo, "OMITIDO", "sin valores temporales en los datos"))
                        continue
                    resp = requests.post(
                        f"{BASE}/api/reports/{op['tipo_v2']}", headers=hdr, timeout=300,
                        json={"indicator_id": iid, "filtros": filtros},
                    )
                elif op["motor"] in ("weasyprint", "pdl_idel"):
                    # Las cards de período mandan `periodo`; el contrato viejo, `tipo`.
                    body = {"engine": op["motor"]}
                    params = op.get("invocacion", {}).get("params") or {}
                    if op["motor"] == "weasyprint":
                        if params.get("periodo"):
                            body["periodo"] = params["periodo"]
                        else:
                            body["tipo"] = params.get("tipo", "evaluacion")
                    resp = requests.post(
                        f"{BASE}/api/indicators/{iid}/export-pdf", headers=hdr, timeout=300, json=body,
                    )
                elif op["motor"] == "docxtpl":
                    informe = op["id"].removeprefix("word_")
                    resp = requests.post(
                        f"{BASE}/api/reports/word/{informe}", headers=hdr, timeout=300,
                        json={"indicator_id": iid, "filtros": {}},
                    )
                else:
                    resumen.append((archivo, "OMITIDO", f"motor desconocido {op['motor']}"))
                    continue

                if resp.ok:
                    (OUT_DIR / archivo).write_bytes(resp.content)
                    kb = len(resp.content) // 1024
                    resumen.append((archivo, "OK", f"{kb} KB"))
                else:
                    detalle = resp.text[:150]
                    try:
                        detalle = resp.json().get("detail", detalle)
                    except Exception:
                        pass
                    resumen.append((archivo, f"ERROR {resp.status_code}", str(detalle)[:150]))
            except Exception as e:  # noqa: BLE001 — herramienta de QA: reportar y seguir
                resumen.append((archivo, "EXCEPCION", str(e)[:150]))

    ancho = max(len(a) for a, _, _ in resumen) if resumen else 20
    print(f"\n{'ARCHIVO'.ljust(ancho)}  ESTADO      DETALLE")
    print("-" * (ancho + 40))
    errores = 0
    for archivo, estado, detalle in resumen:
        if estado.startswith(("ERROR", "EXCEPCION")):
            errores += 1
        print(f"{archivo.ljust(ancho)}  {estado.ljust(10)}  {detalle}")
    print(f"\nTotal: {len(resumen)} | errores: {errores} | salida: {OUT_DIR}")
    return 1 if errores else 0


if __name__ == "__main__":
    raise SystemExit(main())
