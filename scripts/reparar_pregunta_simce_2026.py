"""Repara IN-PLACE la dimensión 'Pregunta' de la carga SIMCE de MAYO 2026.

Contexto
--------
La carga del 2026-05-05 (métrica 5, "Resultados SIMCE por Pregunta") dejó 260
filas SIN la dimensión `Pregunta` (id 11). Causa raíz: `EnrichWithLookup`
usaba `left_on == right_on == "Pregunta"`; pandas colapsa ambas llaves en UNA
sola columna y el paso la borraba después del merge por creerla la copia del
lado derecho. La carga "ganó" Habilidad/Eje Temático y "perdió" Pregunta.

Este script NO borra ni recarga filas: sólo agrega la clave "11" al
`dimensions_json` de las filas que ya existen.

Alineamiento
------------
Para cada grupo (Asignatura, Curso):

1. Se lee la tabla "Forma 1" del `ReportePregunta <curso>.xlsx` con la misma
   lógica que `RunExcelETL` (marker + header_offset=1 + filtro de filas cuya
   primera columna no es numérica).
2. Las filas de la DB se ordenan por `id_data` (el orden de inserción de
   `SaveToMetric` respeta el orden del DataFrame, que a su vez respeta el
   orden del XLS: el merge es `how="left"`).
3. Se EXIGE que cada fila de la DB coincida en CONTENIDO con la fila del XLS
   en la misma posición: (A, B, C, D, E, Correcta, Distractor), con los
   porcentajes del XLS divididos por 100.

Si el conteo de filas difiere, o si alguna posición no coincide en contenido,
el grupo se marca como AMBIGUO y no se toca ninguna fila de ese grupo.

Uso
---
    # dry-run (default, no escribe nada)
    docker exec report_generator-backend-1 \
        python /app/scripts/reparar_pregunta_simce_2026.py --org 1

    # aplicar
    docker exec report_generator-backend-1 \
        python /app/scripts/reparar_pregunta_simce_2026.py --org 1 --apply

Los XLS fuente deben estar bajo `--xls-dir` (default
`/app/data/input/simce_2026`), en subcarpetas cuyo nombre identifique la
asignatura, o con el título de la asignatura dentro del propio Excel.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, "/app")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from backend.database import SessionLocal
from backend.models import MetricData


# ── Constantes verificadas en la DB (org 1) ──────────────────────────────
ID_METRIC = 5           # Resultados SIMCE por Pregunta
DIM_ANIO = "4"
DIM_CURSO = "5"
DIM_ASIGNATURA = "8"
DIM_MES = "9"
DIM_PREGUNTA = "11"

ANIO_OBJETIVO = "2026"
MES_OBJETIVO = "MAYO"

START_MARKER = "forma 1"
HEADER_OFFSET = 1
COLS_XLS = ["Pregunta", "%", "%.1", "%.2", "%.3", "%.4", "Correcta", "Distractor"]
RENOMBRES = {"%": "A", "%.1": "B", "%.2": "C", "%.3": "D", "%.4": "E"}
CAMPOS_VALOR = ["A", "B", "C", "D", "E", "Correcta", "Distractor"]


# ── Lectura de los XLS ───────────────────────────────────────────────────

def _detectar_asignatura(ruta: str) -> Optional[str]:
    """Deduce la asignatura del título del Excel; cae a la ruta si no está."""
    try:
        cabecera = pd.read_excel(ruta, header=None, nrows=8)
        texto = " ".join(str(v) for v in cabecera.to_numpy().ravel()).lower()
    except Exception:
        texto = ""
    ruta_lower = ruta.lower()
    for fuente in (texto, ruta_lower):
        if "matem" in fuente:
            return "Matemáticas"
        if "lenguaje" in fuente:
            return "Lenguaje"
    return None


def _es_clave_numerica(v) -> bool:
    if pd.isna(v):
        return False
    try:
        int(float(str(v).strip()))
        return True
    except Exception:
        return False


def leer_forma1(ruta: str) -> pd.DataFrame:
    """Extrae la tabla 'Forma 1' replicando la lógica de RunExcelETL."""
    df_raw = pd.read_excel(ruta, header=None)
    fila_marker = None
    for i in range(len(df_raw)):
        for v in df_raw.iloc[i]:
            if isinstance(v, str) and START_MARKER in v.strip().lower():
                fila_marker = i
                break
        if fila_marker is not None:
            break
    if fila_marker is None:
        raise ValueError(f"No se encontró el marker '{START_MARKER}' en {ruta}")

    df = pd.read_excel(ruta, header=fila_marker + HEADER_OFFSET)
    df.columns = [str(c).strip() if isinstance(c, str) else c for c in df.columns]
    faltan = [c for c in COLS_XLS if c not in df.columns]
    if faltan:
        raise ValueError(
            f"{os.path.basename(ruta)}: faltan columnas {faltan}. "
            f"Disponibles: {df.columns.tolist()}"
        )
    df = df[df[df.columns[0]].apply(_es_clave_numerica)].reset_index(drop=True)
    return df[COLS_XLS].rename(columns=RENOMBRES)


def _letra_curso(texto: str) -> Optional[str]:
    """'ReportePregunta 2ªA (5).xlsx' → 'A'; 'II C' → 'C'."""
    m = re.search(r"(\d)\s*[ªaº°]\s*([A-Da-d])\b", texto)
    if m:
        return m.group(2).upper()
    m = re.search(r"\b([A-D])\s*$", texto.strip())
    return m.group(1).upper() if m else None


def cargar_xls(xls_dir: str) -> Dict[Tuple[str, str], List[dict]]:
    """Devuelve {(Asignatura, LetraCurso): [filas en orden del XLS]}."""
    rutas = []
    for raiz, _, archivos in os.walk(xls_dir):
        for a in archivos:
            if a.lower().startswith("reportepregunta") and a.lower().endswith((".xlsx", ".xls")):
                rutas.append(os.path.join(raiz, a))
    if not rutas:
        raise SystemExit(f"No se encontraron archivos ReportePregunta*.xlsx en {xls_dir}")

    grupos: Dict[Tuple[str, str], List[dict]] = {}
    for ruta in sorted(rutas):
        nombre = os.path.basename(ruta)
        asignatura = _detectar_asignatura(ruta)
        letra = _letra_curso(nombre)
        if not asignatura or not letra:
            print(f"  ! omitido (no se pudo deducir asignatura/curso): {ruta}")
            continue
        df = leer_forma1(ruta)
        clave = (asignatura, letra)
        if clave in grupos:
            raise SystemExit(
                f"Dos archivos apuntan al mismo grupo {clave}: revisá {xls_dir}"
            )
        grupos[clave] = [
            {"orden": i, "archivo": nombre, "Pregunta": r["Pregunta"],
             **{c: r[c] for c in CAMPOS_VALOR}}
            for i, r in df.iterrows()
        ]
        print(f"  XLS {asignatura:12} {letra}  {nombre:34} filas={len(df)}")
    return grupos


# ── Claves de comparación ────────────────────────────────────────────────

def _num(v, escala: float = 1.0):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        return round(float(v) * escala, 4)
    except (TypeError, ValueError):
        return None


def _txt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip().lower()
    return s or None


def clave_xls(fila: dict) -> tuple:
    return (
        _num(fila["A"], 0.01), _num(fila["B"], 0.01), _num(fila["C"], 0.01),
        _num(fila["D"], 0.01), _num(fila["E"], 0.01),
        _txt(fila["Correcta"]), _txt(fila["Distractor"]),
    )


def clave_db(valor: dict) -> tuple:
    return (
        _num(valor.get("A")), _num(valor.get("B")), _num(valor.get("C")),
        _num(valor.get("D")), _num(valor.get("E")),
        _txt(valor.get("Correcta")), _txt(valor.get("Distractor")),
    )


# ── Lectura de las filas a reparar ───────────────────────────────────────

def cargar_filas_db(db, org_id: int) -> List[dict]:
    filas = []
    for fila in (
        db.query(MetricData)
        .filter(MetricData.id_metric == ID_METRIC, MetricData.org_id == org_id)
        .order_by(MetricData.id_data)
        .all()
    ):
        try:
            dims = json.loads(fila.dimensions_json or "{}")
        except (TypeError, ValueError):
            continue
        if dims.get(DIM_ANIO) != ANIO_OBJETIVO or dims.get(DIM_MES) != MES_OBJETIVO:
            continue
        if str(dims.get(DIM_PREGUNTA, "")).strip():
            continue
        try:
            valor = json.loads(fila.value or "{}")
        except (TypeError, ValueError):
            valor = {}
        filas.append({
            "id_data": fila.id_data,
            "orm": fila,
            "dims": dims,
            "valor": valor,
            "Asignatura": dims.get(DIM_ASIGNATURA),
            "Curso": dims.get(DIM_CURSO),
        })
    return filas


# ── Alineamiento ─────────────────────────────────────────────────────────

def alinear(filas_db: List[dict], grupos_xls: Dict[Tuple[str, str], List[dict]]):
    """Devuelve (asignaciones, incidencias).

    `asignaciones` es [(fila_db, valor_pregunta)] sólo para grupos 100%
    verificados. `incidencias` describe los grupos rechazados.
    """
    por_grupo: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    sin_grupo = []
    for f in filas_db:
        letra = _letra_curso(str(f["Curso"] or ""))
        if not f["Asignatura"] or not letra:
            sin_grupo.append(f)
            continue
        por_grupo[(f["Asignatura"], letra)].append(f)

    asignaciones = []
    incidencias = []
    if sin_grupo:
        incidencias.append(
            f"{len(sin_grupo)} filas sin Asignatura/Curso legible "
            f"(ids: {[f['id_data'] for f in sin_grupo][:10]})"
        )

    for clave, filas in sorted(por_grupo.items()):
        asignatura, letra = clave
        filas = sorted(filas, key=lambda f: f["id_data"])
        xls = grupos_xls.get(clave)
        if xls is None:
            incidencias.append(
                f"{asignatura} {letra}: {len(filas)} filas en DB pero no hay XLS fuente"
            )
            continue
        if len(filas) != len(xls):
            incidencias.append(
                f"{asignatura} {letra}: DB={len(filas)} filas vs XLS={len(xls)} filas"
            )
            continue

        k_db = [clave_db(f["valor"]) for f in filas]
        k_xls = [clave_xls(r) for r in xls]
        discrepancias = [i for i in range(len(k_db)) if k_db[i] != k_xls[i]]
        dup_db = len(set(k_db)) != len(k_db)
        dup_xls = len(set(k_xls)) != len(k_xls)

        if discrepancias:
            detalle = ", ".join(
                f"pos {i} DB={k_db[i]} XLS={k_xls[i]}" for i in discrepancias[:3]
            )
            incidencias.append(
                f"{asignatura} {letra}: {len(discrepancias)} posiciones no coinciden "
                f"en contenido → AMBIGUO, no se toca. {detalle}"
            )
            continue

        for fila, r in zip(filas, xls):
            pregunta = r["Pregunta"]
            try:
                pregunta = str(int(float(pregunta)))
            except (TypeError, ValueError):
                pregunta = str(pregunta).strip()
            asignaciones.append((fila, pregunta))

        marca = " (hay filas con contenido repetido; el orden posicional las desempata)" \
            if (dup_db or dup_xls) else ""
        print(f"  OK  {asignatura:12} {letra}  {len(filas):3} filas alineadas 1:1{marca}")

    return asignaciones, incidencias


# ── Main ─────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org", type=int, default=1, help="org_id (default 1)")
    parser.add_argument(
        "--xls-dir", default="/app/data/input/simce_2026",
        help="Carpeta con los ReportePregunta*.xlsx de mayo 2026",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Escribe los cambios. Sin este flag corre en dry-run.",
    )
    args = parser.parse_args()
    dry_run = not args.apply

    print("=" * 72)
    print(f"Reparación 'Pregunta' — métrica {ID_METRIC}, org {args.org}, "
          f"{MES_OBJETIVO} {ANIO_OBJETIVO}")
    print(f"Modo: {'DRY-RUN (no escribe)' if dry_run else 'APPLY (escribe)'}")
    print("=" * 72)

    print("\nArchivos fuente:")
    grupos_xls = cargar_xls(args.xls_dir)

    db = SessionLocal()
    try:
        filas_db = cargar_filas_db(db, args.org)
        print(f"\nFilas en DB sin dimensión Pregunta: {len(filas_db)}")
        if not filas_db:
            print("Nada que reparar.")
            return 0

        print("\nAlineamiento por grupo:")
        asignaciones, incidencias = alinear(filas_db, grupos_xls)

        no_alineadas = len(filas_db) - len(asignaciones)
        print("\n" + "-" * 72)
        print(f"RESUMEN: alineadas={len(asignaciones)}  no alineadas={no_alineadas}  "
              f"grupos con incidencia={len(incidencias)}")
        for inc in incidencias:
            print(f"  ! {inc}")

        if incidencias:
            print(
                "\nHay grupos ambiguos o incompletos. NO se escribe nada: revisá las "
                "incidencias antes de reintentar."
            )
            return 1

        if dry_run:
            muestra = asignaciones[:5]
            print("\nMuestra de lo que se escribiría:")
            for fila, pregunta in muestra:
                print(f"  id_data={fila['id_data']}  {fila['Asignatura']} "
                      f"{fila['Curso']} → Pregunta={pregunta}")
            print("\nDRY-RUN: no se escribió nada. Repetí con --apply.")
            return 0

        for fila, pregunta in asignaciones:
            dims = dict(fila["dims"])
            dims[DIM_PREGUNTA] = pregunta
            fila["orm"].dimensions_json = json.dumps(dims, ensure_ascii=False)
        db.commit()
        print(f"\nAPPLY: {len(asignaciones)} filas actualizadas con la dimensión Pregunta.")

        restantes = len(cargar_filas_db(db, args.org))
        print(f"Verificación: filas de {MES_OBJETIVO} {ANIO_OBJETIVO} aún sin "
              f"Pregunta = {restantes}")
        return 0 if restantes == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
