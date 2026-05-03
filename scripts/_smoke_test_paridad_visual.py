"""Smoke test del refactor paridad LaTeX — genera un PDF dummy SIN DB.

Llama directamente a _chart_to_png_b64 con records sintéticos y renderiza
el template report_base.html con WeasyPrint. Output:
    data/output/_smoke_paridad_visual.pdf

Sirve para validar visualmente la estética nueva (paleta, tipografía,
header/footer, tablas) antes de tener Docker arriba.

Uso:
    python scripts/_smoke_test_paridad_visual.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

# Evita que el import de modules tire por DATABASE_URL faltante
os.environ.setdefault("DATABASE_URL", "postgresql://x:x@localhost:5432/x")

from rgenerator.core.report_steps import _chart_to_png_b64  # noqa: E402
from jinja2 import Environment, FileSystemLoader  # noqa: E402
from weasyprint import HTML as WeasyprintHTML  # noqa: E402


CURSOS = ["I A", "I B", "II A", "II B", "III A", "III B", "IV A", "IV B"]


def fake_records_estudiantes() -> list[dict]:
    """Records sintéticos: 4 niveles × 8 cursos, ~10 estudiantes c/u."""
    import random
    random.seed(42)
    out = []
    niveles = ["Avanzado", "Intermedio", "Inicial"]
    pesos_por_curso = {
        "I A":  [3, 5, 2], "I B":  [2, 6, 2], "II A": [4, 5, 1], "II B": [3, 4, 3],
        "III A": [5, 4, 1], "III B": [4, 5, 1], "IV A": [6, 3, 1], "IV B": [5, 4, 1],
    }
    for curso in CURSOS:
        pesos = pesos_por_curso[curso]
        for nivel, n in zip(niveles, pesos):
            base = {"Avanzado": 0.85, "Intermedio": 0.6, "Inicial": 0.35}[nivel]
            for _ in range(n):
                logro = max(0.0, min(1.0, base + random.uniform(-0.1, 0.1)))
                out.append({
                    "_curso": curso,
                    "_nivel_de_logro": nivel,
                    "_logro_1": logro,
                    "_hito": "Diagnóstico",
                })
    return out


def fake_records_preguntas() -> list[dict]:
    """Records sintéticos por eje × habilidad × curso."""
    import random
    random.seed(7)
    ejes = ["Números", "Álgebra", "Geometría", "Datos"]
    habilidades = ["Resolver", "Modelar", "Argumentar"]
    out = []
    for curso in CURSOS:
        for eje in ejes:
            for _ in range(5):
                out.append({
                    "_curso": curso, "_eje_tematico": eje,
                    "_logro_1": random.uniform(0.3, 0.9),
                    "_hito": "Diagnóstico",
                })
        for hab in habilidades:
            for _ in range(5):
                out.append({
                    "_curso": curso, "_habilidad": hab,
                    "_logro_1": random.uniform(0.4, 0.85),
                    "_hito": "Diagnóstico",
                })
    return out


def main():
    out_dir = ROOT / "data" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "_smoke_paridad_visual.pdf"

    estudiantes = fake_records_estudiantes()
    preguntas = fake_records_preguntas()
    print(f"Records: {len(estudiantes)} estudiantes, {len(preguntas)} preguntas")

    # Indicator dummy con achievement_levels para que el StackedCount use semáforo
    class DummyIndicator:
        column_roles = {}
        role_formats = {}
        achievement_levels = '[{"name":"Avanzado","color":"#1f9e89"},{"name":"Intermedio","color":"#f1a340"},{"name":"Inicial","color":"#e64b35"}]'

    indicator = DummyIndicator()

    # Generar gráficos (mismos componentes que el pdf_layout DIA real)
    print("Generando gráficos...")
    chart_logro_curso = _chart_to_png_b64(
        {"component": "BarByGroup", "valueField": "_logro_1", "groupField": "_curso", "showValues": True},
        estudiantes, indicator)
    chart_alumnos_nivel = _chart_to_png_b64(
        {"component": "StackedCountByGroup", "groupField": "_curso", "levelField": "_nivel_de_logro"},
        estudiantes, indicator)
    chart_logro_eje = _chart_to_png_b64(
        {"component": "BarByGroup", "valueField": "_logro_1", "groupField": "_eje_tematico"},
        preguntas, indicator)
    chart_logro_hab = _chart_to_png_b64(
        {"component": "BarByGroup", "valueField": "_logro_1", "groupField": "_habilidad"},
        preguntas, indicator)

    # Tabla resumen sintética
    tabla_columns = ["Curso", "Alumnos", "Promedio", "Mínimo", "Máximo"]
    tabla_rows = []
    by_curso = {}
    for r in estudiantes:
        by_curso.setdefault(r["_curso"], []).append(r["_logro_1"])
    for curso in CURSOS:
        vals = by_curso.get(curso, [])
        if vals:
            tabla_rows.append([
                curso, str(len(vals)),
                f"{sum(vals)/len(vals):.0%}",
                f"{min(vals):.0%}",
                f"{max(vals):.0%}",
            ])

    # Branding sintético (sin imágenes reales — solo texto, para validar layout)
    branding = {
        "left_image_b64": None,
        "left_image_ct": None,
        "right_image_b64": None,
        "right_image_ct": None,
        "center_header": [
            "Liceo Pullinque",
            "DIA Diagnóstico — Matemáticas",
            "Mayo 2026",
        ],
        "left_footer": "Miguel Godoy Díaz",
        "show_page_number": True,
    }

    sections = [
        {"type": "page_title",
         "title": "Informe DIA — Por evaluación",
         "subtitle": "Resumen del hito seleccionado",
         "filters_label": "Hito: Diagnóstico"},
        {"type": "table",
         "heading": "Cuadro Resumen Logro por Curso",
         "columns": tabla_columns, "rows": tabla_rows},
        {"type": "chart",
         "heading": "Logro Promedio por Curso",
         "image_b64": chart_logro_curso},
        {"type": "chart",
         "heading": "Cantidad de Alumnos por Nivel de Logro",
         "image_b64": chart_alumnos_nivel},
        {"type": "chart",
         "heading": "Logro Promedio por Eje Temático",
         "image_b64": chart_logro_eje},
        {"type": "chart",
         "heading": "Logro Promedio por Habilidad",
         "image_b64": chart_logro_hab},
    ]

    # Render con Jinja2 + WeasyPrint
    templates_dir = ROOT / "backend" / "rgenerator" / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=False)
    template = env.get_template("report_base.html")
    html_str = template.render(
        sections=sections,
        org_name="Fundación PHP",
        report_date=date.today().strftime("%d/%m/%Y"),
        branding=branding,
    )

    # Persistir HTML para inspección rápida
    html_path = out_dir / "_smoke_paridad_visual.html"
    html_path.write_text(html_str, encoding="utf-8")
    print(f"  HTML escrito: {html_path}")

    print("Renderizando PDF con WeasyPrint...")
    pdf_bytes = WeasyprintHTML(string=html_str, base_url=str(ROOT)).write_pdf()
    out_path.write_bytes(pdf_bytes)
    size = out_path.stat().st_size
    print(f"\n✅ PDF generado: {out_path} ({size:,} bytes)")


if __name__ == "__main__":
    main()
