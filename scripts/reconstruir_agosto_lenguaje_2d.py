"""Reconstruye metric 5 (SIMCE preguntas) para LENGUAJE Agosto 2°D
desde el archivo detallada lenguaje.xlsx.

Algoritmo:
1. Lee `Puntajes` (1/0 por estudiante × pregunta) y `Matriz de
   Respuestas` (a/b/c/d/o) del XLSX.
2. Por cada pregunta, infiere la respuesta correcta tomando la letra
   más frecuente entre los que sacaron 1.
3. Calcula distribución de respuestas (% por A/B/C/D/E) sobre los 26
   estudiantes del 2°D, identifica distractor principal y % de la
   correcta = Logro.
4. Borra los 40 rows existentes de metric 5 con (LENGUAJE, AGOSTO,
   2°D) — son los que estaban cargados desde un ReportePregunta del
   cliente y vamos a reemplazarlos con el cálculo de la fuente cruda.
5. Inserta 40 rows reconstruidos con dimensiones completas pero
   Habilidad y Eje Temático EN BLANCO (sin dimensions_json para esas
   keys), tal como pidió Miguel.

Cobertura: solo 2°D (lo único que tiene el archivo). 2°A, 2°B y 2°C
de Agosto Lenguaje siguen siendo pendientes — requieren archivos
ReportePregunta o detallada del cliente para esos cursos.

Ejecutar (en container con archivo en /tmp):
    docker cp ".../detallada lenguaje.xlsx" report_generator-backend-1:/tmp/det_ag.xlsx
    docker exec report_generator-backend-1 python /app/scripts/reconstruir_agosto_lenguaje_2d.py /tmp/det_ag.xlsx
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime

sys.path.insert(0, "/app")

import pandas as pd

from backend.database import SessionLocal
from backend.models import Dimension, MetricData, MetricDimension, User


# IDs verificados via psql (org_id=1)
DIMS = {
    "Establecimiento": 3,
    "Año": 4,
    "Curso": 5,
    "Nombre": 7,    # no se usa en preguntas pero por completitud
    "Asignatura": 8,
    "Mes": 9,
    "N Prueba": 10,
    "Pregunta": 11,
    # "Habilidad": 12,    # blanco
    # "Eje Temático": 13, # blanco
}

ASIGNATURA = "LENGUAJE"
ANIO = "2025"
MES = "AGOSTO"
N_PRUEBA = "3"
CURSO_DB = "II D"        # como aparece en el resto de metric_data
ESTABLECIMIENTO = "Pullinque"
METRIC_ID = 5


def _normalize_letter(v):
    if v is None:
        return None
    s = str(v).strip().lower()
    if not s or s in ("nan",):
        return None
    return s


def main():
    if len(sys.argv) < 2:
        print("Uso: python reconstruir_agosto_lenguaje_2d.py <ruta_detallada.xlsx>")
        sys.exit(1)
    src = sys.argv[1]

    # 1. Cargar
    df_p = pd.read_excel(src, sheet_name="Puntajes", header=1)
    df_m = pd.read_excel(src, sheet_name="Matriz de Respuestas", header=1)
    print(f"Puntajes: {df_p.shape}, Matriz: {df_m.shape}")

    # Validar
    pregunta_cols = [c for c in df_p.columns if isinstance(c, int)]
    if not pregunta_cols:
        # Las columnas pueden venir como strings "1", "2"
        pregunta_cols = [c for c in df_p.columns if str(c).isdigit()]
    print(f"Preguntas detectadas: {len(pregunta_cols)} (cols {pregunta_cols[:5]}...{pregunta_cols[-3:]})")

    cursos = df_p["Curso"].unique()
    print(f"Cursos en archivo: {list(cursos)}")
    if len(cursos) != 1:
        print(f"⚠ Esperaba 1 curso, encontré {len(cursos)}. Filtrando solo 2°D.")

    # Filtrar solo 2°D (por si acaso)
    df_p = df_p[df_p["Curso"].str.contains("D", na=False)].reset_index(drop=True)
    df_m = df_m[df_m["Curso"].str.contains("D", na=False)].reset_index(drop=True)
    n_estudiantes = len(df_p)
    print(f"Estudiantes 2°D: {n_estudiantes}")

    # 2. Inferir respuestas correctas
    print("\n== Inferencia de respuestas correctas ==")
    correctas = {}
    for q in pregunta_cols:
        # Estudiantes con puntaje 1 en esta pregunta
        mask = df_p[q] == 1
        if mask.sum() == 0:
            print(f"  P{q}: 0 acertaron — no se puede inferir, queda null")
            correctas[q] = None
            continue
        letras_correctas = df_m.loc[mask, q].apply(_normalize_letter).dropna().tolist()
        if not letras_correctas:
            correctas[q] = None
            continue
        # Mayoría
        c = Counter(letras_correctas)
        top, n_top = c.most_common(1)[0]
        if len(c) > 1:
            # Hay disagreement — algo raro, log
            print(f"  P{q}: {dict(c)} → correcta = '{top.upper()}' ({n_top}/{len(letras_correctas)})")
        correctas[q] = top.upper()

    # 3. Calcular distribución por pregunta sobre todos los estudiantes
    print("\n== Cálculo de distribuciones ==")
    rows_to_insert = []
    for q in pregunta_cols:
        respuestas = df_m[q].apply(_normalize_letter).dropna().tolist()
        n_total = len(respuestas)  # estudiantes con respuesta válida (excluye NaN)
        c = Counter(respuestas)
        # %s por letra
        pct = {letra.upper(): round((c.get(letra, 0) / n_total) * 100, 2) if n_total > 0 else 0.0
               for letra in ["a", "b", "c", "d", "e"]}
        # 'o' (omitida) no se reporta como alternativa, va al campo "Logro" implícito
        correcta = correctas.get(q)
        logro = (pct.get(correcta, 0.0) / 100.0) if correcta else 0.0
        # Distractor: letra ≠ correcta con mayor %
        distractor = None
        if correcta:
            otros = {k: v for k, v in pct.items() if k != correcta}
            if otros:
                distractor = max(otros.items(), key=lambda kv: kv[1])[0]

        rows_to_insert.append({
            "Pregunta": q,
            "A": pct["A"], "B": pct["B"], "C": pct["C"], "D": pct["D"], "E": pct["E"],
            "Correcta": correcta or "",
            "Distractor": distractor or "",
            "Logro": round(logro, 4),
        })
        print(f"  P{q}: A={pct['A']:.0f}% B={pct['B']:.0f}% C={pct['C']:.0f}% D={pct['D']:.0f}% E={pct['E']:.0f}% → correcta={correcta} Logro={logro:.2f}")

    # 4-5. DB ops
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.role == "admin").first()
        org_id = admin.org_id

        # Borrar rows existentes
        print("\n== Borrando rows existentes (metric 5, LENGUAJE Agosto, 2°D) ==")
        existing = db.query(MetricData).filter(
            MetricData.id_metric == METRIC_ID,
            MetricData.org_id == org_id,
        ).all()
        n_borrar = 0
        for r in existing:
            try:
                dims = json.loads(r.dimensions_json) if isinstance(r.dimensions_json, str) else (r.dimensions_json or {})
            except Exception:
                continue
            if (dims.get(str(DIMS["Asignatura"])) == ASIGNATURA
                and dims.get(str(DIMS["Mes"])) == MES
                and dims.get(str(DIMS["Curso"])) == CURSO_DB):
                db.delete(r)
                n_borrar += 1
        db.commit()
        print(f"  borrados: {n_borrar}")

        # Insertar reconstruidos
        print("\n== Insertando rows reconstruidos ==")
        n_insert = 0
        for r in rows_to_insert:
            dims_json = {
                str(DIMS["Establecimiento"]): ESTABLECIMIENTO,
                str(DIMS["Asignatura"]): ASIGNATURA,
                str(DIMS["Año"]): ANIO,
                str(DIMS["Mes"]): MES,
                str(DIMS["N Prueba"]): N_PRUEBA,
                str(DIMS["Curso"]): CURSO_DB,
                str(DIMS["Pregunta"]): str(r["Pregunta"]),
            }
            val_obj = {
                "A": r["A"], "B": r["B"], "C": r["C"], "D": r["D"], "E": r["E"],
                "Correcta": r["Correcta"],
                "Distractor": r["Distractor"],
                "Logro": r["Logro"],
            }
            db.add(MetricData(
                id_metric=METRIC_ID,
                value=json.dumps(val_obj, ensure_ascii=False),
                dimensions_json=json.dumps(dims_json, ensure_ascii=False),
                created_at=datetime.utcnow(),
                org_id=org_id,
            ))
            n_insert += 1
        db.commit()
        print(f"  insertados: {n_insert}")
    finally:
        db.close()

    print("\nDONE")


if __name__ == "__main__":
    main()
