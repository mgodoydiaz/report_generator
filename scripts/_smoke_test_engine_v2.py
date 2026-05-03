"""Smoke test del motor PDF v2 (backend/rgenerator/reports/).

Genera 2 PDFs (DIA + SIMCE) con DataFrames sintéticos y los escribe en
data/output/. Sin DB, sin endpoint — solo verifica que la cadena
charts → tables → runtime → WeasyPrint → PDF funciona end-to-end.

Uso (desde el container Docker):
    docker exec -w /app report_generator-backend-1 \
        python scripts/_smoke_test_engine_v2.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from rgenerator.reports.simce import crear_informe as simce_informe
from rgenerator.reports.dia import crear_informe as dia_informe


CURSOS = ["I A", "I B", "II A", "II B", "III A", "III B", "IV A", "IV B"]
NIVELES_DIA = ["Avanzado", "Intermedio", "Inicial"]
NIVELES_SIMCE = ["Adecuado", "Elemental", "Insuficiente"]
EJES_MAT = ["Números", "Álgebra", "Geometría", "Datos"]
HABS = ["Resolver", "Modelar", "Argumentar", "Representar"]
MESES = ["ABRIL", "JUNIO", "AGOSTO", "OCTUBRE", "NOVIEMBRE"]


def _df_dia_estudiantes() -> pd.DataFrame:
    random.seed(1)
    rows = []
    n_lista = 1
    for curso in CURSOS:
        for nivel, base in [("Avanzado", 0.85), ("Intermedio", 0.55), ("Inicial", 0.30)]:
            n = random.randint(3, 8)
            for _ in range(n):
                logro = max(0.0, min(1.0, base + random.uniform(-0.10, 0.10)))
                rows.append({
                    "Curso": curso,
                    "Nivel": "Primeros Medios" if curso.startswith("I") else "Segundos Medios",
                    "Logro": logro,
                    "NIVEL DE LOGRO": nivel,
                    "Número de Lista": n_lista,
                    "Nombre del Estudiante": f"APELLIDO {n_lista:02d} NOMBRE",
                })
                n_lista += 1
    return pd.DataFrame(rows)


def _df_dia_preguntas() -> pd.DataFrame:
    random.seed(2)
    rows = []
    for curso in CURSOS:
        for n_preg in range(1, 31):
            eje = random.choice(EJES_MAT)
            hab = random.choice(HABS)
            logro = random.uniform(0.20, 0.80)
            nivel = "Avanzado" if logro > 0.65 else ("Intermedio" if logro > 0.40 else "Inicial")
            rows.append({
                "Curso": curso,
                "N° Pregunta": n_preg,
                "Eje Temático": eje,
                "Habilidad": hab,
                "Logro": logro,
                "Nivel de Logro": nivel,
            })
    return pd.DataFrame(rows)


def _df_simce_estudiantes() -> pd.DataFrame:
    random.seed(3)
    rows = []
    for curso in ["2A", "2B", "2C", "2D"]:
        for n_prueba, mes in enumerate(MESES, start=1):
            for nivel, base_rend, base_simce in [
                ("Adecuado", 0.80, 290),
                ("Elemental", 0.55, 250),
                ("Insuficiente", 0.30, 220),
            ]:
                n = random.randint(2, 6)
                for i in range(n):
                    rend = max(0.0, min(1.0, base_rend + random.uniform(-0.10, 0.10)))
                    simce = base_simce + random.randint(-15, 15)
                    rows.append({
                        "Curso": curso,
                        "Asignatura": "LENGUAJE",
                        "Numero_Prueba": n_prueba,
                        "Mes": mes,
                        "Nombre": f"APELLIDO {curso} {n_prueba}-{i:02d}",
                        "Rend": rend,
                        "SIMCE": simce,
                        "Logro": nivel,
                        "Avance_Promedio": random.uniform(0.0, 0.05),
                    })
    return pd.DataFrame(rows)


def _df_simce_preguntas() -> pd.DataFrame:
    random.seed(4)
    rows = []
    for curso in ["2A", "2B", "2C", "2D"]:
        for n_preg in range(1, 31):
            rows.append({
                "Curso": curso,
                "Asignatura": "LENGUAJE",
                "Numero_Prueba": 5,
                "Pregunta": n_preg,
                "Habilidad": random.choice(HABS),
                "Eje temático": random.choice(["Lectura", "Escritura"]),
                "Logro": random.uniform(0.3, 0.85),
                "A": random.randint(5, 25),
                "B": random.randint(5, 25),
                "C": random.randint(5, 25),
                "D": random.randint(5, 25),
                "E": random.randint(0, 5),
                "Correcta": random.choice(["A", "B", "C", "D"]),
                "Distractor": random.choice(["A", "B", "C", "D"]),
            })
    return pd.DataFrame(rows)


def main():
    out_dir = ROOT / "data" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Generando DIA...")
    df_dia_e = _df_dia_estudiantes()
    df_dia_p = _df_dia_preguntas()
    print(f"  estudiantes: {len(df_dia_e)} filas, preguntas: {len(df_dia_p)} filas")
    pdf_dia = dia_informe.construir(
        df_dia_e, df_dia_p,
        overrides={"branding": {
            "left_image": "logo_php.png",
            "right_image": "pullinque_php.png",
            "center_header": [
                "Informe DIA Diagnóstico",
                "Matemáticas Nivel Medio",
                "Mayo 2026",
            ],
            "left_footer": "Miguel Godoy Díaz",
            "show_page_number": True,
        }},
    )
    out_dia = out_dir / "_engine_v2_dia.pdf"
    out_dia.write_bytes(pdf_dia)
    print(f"  ✓ DIA: {out_dia} ({out_dia.stat().st_size:,} bytes)")

    print("Generando SIMCE...")
    df_s_e = _df_simce_estudiantes()
    df_s_p = _df_simce_preguntas()
    print(f"  estudiantes: {len(df_s_e)} filas, preguntas: {len(df_s_p)} filas")
    pdf_simce = simce_informe.construir(
        df_s_e, df_s_p,
        asignatura="LENGUAJE",
        numero_prueba=5,
        overrides={"branding": {
            "left_image": "logo_php.png",
            "right_image": "pullinque_php.png",
            "center_header": [
                "Informe Ensayo SIMCE N° 5",
                "Lenguaje 2° Medio",
                "Noviembre 2025",
            ],
            "left_footer": "Miguel Godoy Díaz",
            "show_page_number": True,
        }},
    )
    out_simce = out_dir / "_engine_v2_simce.pdf"
    out_simce.write_bytes(pdf_simce)
    print(f"  ✓ SIMCE: {out_simce} ({out_simce.stat().st_size:,} bytes)")

    print("\n✅ Smoke test motor PDF v2 OK")


if __name__ == "__main__":
    main()
