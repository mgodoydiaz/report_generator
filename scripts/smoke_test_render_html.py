"""Smoke test del RenderHtmlReport con datos mock (sin tocar Supabase).

Genera DataFrames sintéticos de SIMCE Lenguaje 2° Medio, ejecuta las funciones
reales de plot_tools y report_tools para producir aux_files (PNGs y XLSX),
construye un RunContext mínimo y ejecuta RenderHtmlReport. El PDF resultante
se guarda en data/output/smoke_test_render_html.pdf para QA visual contra
docs/pdf_examples/Informe SIMCE 5 Lenguaje.pdf.

Uso:
    conda activate rgenerator
    python scripts/smoke_test_render_html.py
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# PYTHONPATH setup (no requiere pip install -e .)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from rgenerator.core.context import RunContext  # noqa: E402
from rgenerator.core.report_steps import RenderHtmlReport  # noqa: E402
from rgenerator.tooling import plot_tools, report_tools  # noqa: E402

AUX_DIR = ROOT / "data" / "tmp" / "smoke_aux_simce"
OUTPUT_DIR = ROOT / "data" / "output"
SCHEMA_PATH = ROOT / "backend" / "schemas" / "esquema_informe_lenguaje.json"
OUTPUT_PDF = "smoke_test_render_html.pdf"


# ────────────────────────────── Mock data ─────────────────────────────────────


def make_mock_data(seed: int = 42) -> tuple[pd.DataFrame, pd.DataFrame]:
    """DataFrames mock con la forma que el ETL real produce."""
    rng = np.random.default_rng(seed)
    cursos = ["2A", "2B", "2C", "2D"]
    meses = ["ABRIL", "JUNIO", "AGOSTO", "OCTUBRE", "NOVIEMBRE"]
    niveles_orden = ["Insuficiente", "Elemental", "Adecuado"]

    # ── Estudiantes ──
    rows = []
    for ci, curso in enumerate(cursos):
        for mi, mes in enumerate(meses):
            n = int(rng.integers(22, 34))
            base = 0.45 + 0.05 * ci + 0.02 * mi  # ligero efecto curso/mes
            for i in range(n):
                rend = float(np.clip(rng.normal(base, 0.13), 0.05, 0.95))
                simce = int(150 + rend * 200 + rng.normal(0, 10))
                if rend > 0.65:
                    nivel = "Adecuado"
                elif rend > 0.4:
                    nivel = "Elemental"
                else:
                    nivel = "Insuficiente"
                rows.append({
                    "Nombre": f"Estudiante {curso}-{mes[:3]}-{i + 1:02d}",
                    "RUT": f"{20_000_000 + int(rng.integers(0, 5_000_000))}-{int(rng.integers(0, 9))}",
                    "Curso": curso,
                    "Mes": mes,
                    "Numero_Prueba": mi + 1,
                    "Asignatura": "LENGUAJE",
                    "Rend": rend,
                    "SIMCE": simce,
                    "Logro": nivel,
                })
    df_est = pd.DataFrame(rows)

    # ── Preguntas (solo Numero_Prueba=5 con datos completos por curso) ──
    habs = ["EVALUAR", "INFERIR", "INTERPRETAR", "LOCALIZAR", "SINTETIZAR"]
    ejes = ["Lectura literal", "Lectura inferencial", "Reflexión sobre el texto"]
    rows_p = []
    for curso in cursos:
        for q in range(1, 41):
            hab = habs[q % len(habs)]
            eje = ejes[q % len(ejes)]
            logro = float(np.clip(rng.normal(0.55, 0.13), 0.1, 0.95))
            n = int(rng.integers(20, 35))
            correct_ans = ["a", "b", "c", "d"][q % 4]
            distract = ["a", "b", "c", "d"][(q + 1) % 4]
            # respuestas A/B/C/D sumando ~n
            answers = rng.multinomial(n, [0.25, 0.25, 0.25, 0.25])
            rows_p.append({
                "Curso": curso,
                "Pregunta": q,
                "Habilidad": hab,
                "Eje temático": eje,
                "Numero_Prueba": 5,
                "Asignatura": "LENGUAJE",
                "Logro": logro,
                "A": int(answers[0]),
                "B": int(answers[1]),
                "C": int(answers[2]),
                "D": int(answers[3]),
                "E": 0,
                "Correcta": correct_ans,
                "Distractor": distract,
            })
    df_preg = pd.DataFrame(rows_p)

    return df_est, df_preg


# ────────────────────────────── Aux files ─────────────────────────────────────


def setup_dirs() -> None:
    if AUX_DIR.exists():
        shutil.rmtree(AUX_DIR)
    AUX_DIR.mkdir(parents=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def generate_aux_files(df_est: pd.DataFrame, df_preg: pd.DataFrame) -> None:
    """Llena AUX_DIR con todos los archivos que el esquema referencia."""
    df_est_p = df_est[df_est["Numero_Prueba"] == 5].copy()

    # ── Tablas (XLSX) ──
    report_tools.resumen_estadistico_basico(
        df_est_p, "Rend", formato="percent", agrupar_por="Curso"
    ).to_excel(AUX_DIR / "resumen_logro_por_curso.xlsx", index=False)

    report_tools.resumen_estadistico_basico(
        df_est_p, "SIMCE", formato="number", agrupar_por="Curso"
    ).to_excel(AUX_DIR / "resumen_simce_por_curso.xlsx", index=False)

    report_tools.crear_tabla_estadistica_por_pregunta(
        df_preg, parametros={"Asignatura": "LENGUAJE", "Numero_Prueba": 5}
    ).to_excel(AUX_DIR / "reporte_preguntas.xlsx", index=False)

    # ── Gráficos (PNG) ──
    plot_tools.grafico_barras_promedio_por(
        df_est_p, "Rend",
        titulo="Rendimiento Promedio por Curso", ylabel="Rendimiento (%)",
        nombre_grafico=str(AUX_DIR / "rendimiento_promedio_por_curso.png"),
    )

    plot_tools.boxplot_valor_por_curso(
        df_est_p, "SIMCE",
        titulo_grafico="Distribución de Puntaje SIMCE por Curso",
        ylabel="Puntaje SIMCE", formato="number",
        nombre_grafico=str(AUX_DIR / "distribucion_puntaje_simce_por_curso.png"),
    )

    plot_tools.valor_promedio_agrupado_por(
        df_est, columna_valor="Rend",
        agrupar_principal_por="Curso", agrupar_secundario_por="Mes",
        titulo_grafico="Evolución del Logro Promedio por Curso y Mes",
        titulo_leyenda="Mes", y_lims=(0, 1), formato="percent",
        nombre_grafico=str(AUX_DIR / "evolucion_logro_promedio_por_curso_y_mes.png"),
    )

    plot_tools.valor_promedio_agrupado_por(
        df_est, columna_valor="SIMCE",
        agrupar_principal_por="Curso", agrupar_secundario_por="Mes",
        titulo_grafico="Evolución del SIMCE Promedio por Curso y Mes",
        titulo_leyenda="Mes", formato="number",
        nombre_grafico=str(AUX_DIR / "evolucion_simce_promedio_por_curso_y_mes.png"),
    )

    plot_tools.alumnos_por_nivel_cualitativo(
        df_est_p, columna_nivel="Logro", agrupar_por="Curso",
        titulo_grafico="Cantidad de Alumnos por Nivel de Logro y Curso",
        titulo_leyenda="Nivel de Logro", ylabel="Cantidad de Alumnos",
        nombre_grafico=str(AUX_DIR / "alumnos_por_nivel.png"),
    )

    plot_tools.alumnos_por_nivel_curso_y_mes(
        df_est, columna_nivel="Logro",
        titulo_grafico="", titulo_leyenda="Nivel de Logro",
        ylabel="Cantidad de Alumnos",
        nombre_grafico=str(AUX_DIR / "evolucion_alumnos_por_nivel.png"),
    )

    plot_tools.valor_promedio_agrupado_por(
        df_preg, columna_valor="Logro",
        agrupar_principal_por="Curso", agrupar_secundario_por="Habilidad",
        titulo_grafico="Logro Promedio por Habilidad",
        titulo_leyenda="Habilidad", formato="percent",
        nombre_grafico=str(AUX_DIR / "logro_promedio_por_habilidad.png"),
    )

    plot_tools.valor_promedio_agrupado_por(
        df_preg, columna_valor="Logro",
        agrupar_principal_por="Curso", agrupar_secundario_por="Eje temático",
        titulo_grafico="Logro Promedio por Eje Temático",
        titulo_leyenda="Eje Temático", formato="percent",
        nombre_grafico=str(AUX_DIR / "logro_promedio_por_eje.png"),
    )


# ────────────────────────────── Run ──────────────────────────────────────────


def run() -> Path:
    setup_dirs()
    print(f"[smoke] aux_dir={AUX_DIR}")
    print(f"[smoke] output_dir={OUTPUT_DIR}")

    df_est, df_preg = make_mock_data()
    print(f"[smoke] mock estudiantes: {len(df_est)} filas — preguntas: {len(df_preg)} filas")

    generate_aux_files(df_est, df_preg)
    aux_files = sorted(AUX_DIR.iterdir())
    print(f"[smoke] aux_files generados ({len(aux_files)}):")
    for f in aux_files:
        print(f"  - {f.name} ({f.stat().st_size} bytes)")

    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)

    # Las rutas en el esquema empiezan con "aux_files/..." (relativas).
    # RenderHtmlReport las resuelve contra ctx.aux_dir, así que renombramos
    # para que `aux_files/X` se mapee a `AUX_DIR/X`. Lo más limpio: ajustar
    # el contenido del esquema in-memory para usar solo el basename.
    for s in schema.get("secciones_fijas", []) + schema.get("secciones_dinamicas", []):
        cont = s.get("contenido", "")
        if cont.startswith("aux_files/"):
            s["contenido"] = cont[len("aux_files/"):]

    ctx = RunContext(
        evaluation="smoke_simce_lenguaje",
        run_id="smoke_001",
        base_dir=ROOT,
        aux_dir=AUX_DIR,
        outputs_dir=OUTPUT_DIR,
        params={"report_schema": schema},
    )

    step = RenderHtmlReport(report_schema=schema, output_filename=OUTPUT_PDF)
    step.run(ctx)

    pdf_path = ctx.outputs.get("report_pdf")
    if pdf_path and Path(pdf_path).exists():
        size = Path(pdf_path).stat().st_size
        print(f"\n✅ PDF generado: {pdf_path} ({size:,} bytes)")
        return Path(pdf_path)
    raise RuntimeError("No se generó PDF")


if __name__ == "__main__":
    run()
