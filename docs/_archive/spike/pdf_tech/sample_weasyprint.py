"""
Spike PDF — WeasyPrint
Genera un informe de ejemplo con: portada, tabla de resultados y gráfico (PNG embebido).
"""

import base64
import io
import sys
from pathlib import Path

# ── Gráfico de barras con matplotlib (server-side) ──────────────────────────

def bar_chart_png_b64():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    asignaturas = ["Lenguaje", "Matemática", "Ciencias", "Historia"]
    logros = [62, 54, 71, 48]
    colores = ["#6366f1", "#8b5cf6", "#06b6d4", "#f59e0b"]

    fig, ax = plt.subplots(figsize=(6, 3))
    bars = ax.bar(asignaturas, logros, color=colores, width=0.55, zorder=3)
    ax.set_ylim(0, 100)
    ax.set_ylabel("% Logro", fontsize=9)
    ax.set_title("Logro por asignatura — 4° básico", fontsize=11, fontweight="bold")
    ax.yaxis.grid(True, linestyle="--", alpha=0.5, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    for bar, val in zip(bars, logros):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 1.5,
                f"{val}%", ha="center", va="bottom", fontsize=8, fontweight="bold")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()

# ── HTML del informe ─────────────────────────────────────────────────────────

ESTUDIANTES = [
    ("García, Valentina",  "4°A", 74, "Alto"),
    ("Muñoz, Sebastián",   "4°A", 58, "Medio"),
    ("López, Camila",      "4°B", 81, "Alto"),
    ("Rojas, Diego",       "4°B", 43, "Bajo"),
    ("Herrera, Isidora",   "4°A", 67, "Medio"),
    ("Soto, Matías",       "4°B", 55, "Medio"),
]

NIVEL_COLOR = {"Alto": "#dcfce7", "Medio": "#fef9c3", "Bajo": "#fee2e2"}

def build_html(chart_b64: str) -> str:
    rows = ""
    for nombre, curso, puntaje, nivel in ESTUDIANTES:
        bg = NIVEL_COLOR.get(nivel, "#fff")
        rows += f"""
        <tr style="background:{bg}">
          <td>{nombre}</td><td>{curso}</td>
          <td style="text-align:center">{puntaje}</td>
          <td style="text-align:center"><span class="nivel">{nivel}</span></td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<style>
  @page {{ size: A4; margin: 2cm 2.2cm; }}
  body {{ font-family: "Segoe UI", Arial, sans-serif; font-size: 10pt; color: #1e293b; margin: 0; }}

  /* PORTADA */
  .cover {{ display: flex; flex-direction: column; justify-content: center;
            align-items: center; height: 24cm; text-align: center; }}
  .cover h1 {{ font-size: 28pt; color: #4f46e5; margin-bottom: 0.3cm; }}
  .cover .subtitle {{ font-size: 13pt; color: #64748b; margin-bottom: 1cm; }}
  .cover .meta {{ font-size: 9pt; color: #94a3b8; }}
  .cover .logo-bar {{ width: 120px; height: 6px;
                      background: linear-gradient(90deg, #6366f1, #06b6d4);
                      border-radius: 3px; margin: 0.6cm auto; }}

  /* SALTO */
  .page-break {{ page-break-before: always; }}

  /* CUERPO */
  h2 {{ font-size: 14pt; color: #4f46e5; border-bottom: 2px solid #e0e7ff;
        padding-bottom: 4px; margin-top: 1cm; }}
  p  {{ line-height: 1.6; color: #334155; }}

  /* TABLA */
  table {{ width: 100%; border-collapse: collapse; margin-top: 0.5cm; font-size: 9pt; }}
  th {{ background: #4f46e5; color: white; padding: 6px 10px; text-align: left; }}
  td {{ padding: 5px 10px; border-bottom: 1px solid #e2e8f0; }}
  .nivel {{ padding: 2px 8px; border-radius: 12px; font-weight: bold;
            font-size: 8pt; background: rgba(0,0,0,0.06); }}

  /* GRÁFICO */
  .chart-wrap {{ margin-top: 0.7cm; text-align: center; }}
  .chart-wrap img {{ max-width: 14cm; }}
  .caption {{ font-size: 8pt; color: #64748b; margin-top: 4px; }}

  /* FOOTER */
  .footer {{ position: running(footer); text-align: right;
             font-size: 7.5pt; color: #94a3b8; }}
  @page {{ @bottom-right {{ content: element(footer); }} }}
</style>
</head>
<body>

<div class="footer">Fundación PHP · Evaluación 2024</div>

<!-- PORTADA -->
<div class="cover">
  <div class="logo-bar"></div>
  <h1>Informe de Resultados</h1>
  <div class="subtitle">Evaluación PDL — 4° Básico · 2024</div>
  <div class="meta">
    Establecimiento: Colegio Demo S/N<br>
    Fecha de generación: 20 de abril de 2026<br>
    Generado con <strong>WeasyPrint 68</strong>
  </div>
  <div class="logo-bar"></div>
</div>

<!-- PÁGINA 2 -->
<div class="page-break"></div>

<h2>Resumen de resultados</h2>
<p>
  La siguiente tabla muestra el desempeño individual de los estudiantes evaluados en
  la prueba PDL aplicada durante el primer semestre de 2024. Los niveles de logro se
  clasifican en <strong>Alto</strong> (≥70), <strong>Medio</strong> (50–69) y
  <strong>Bajo</strong> (&lt;50).
</p>

<table>
  <thead>
    <tr>
      <th>Estudiante</th><th>Curso</th><th>Puntaje</th><th>Nivel</th>
    </tr>
  </thead>
  <tbody>{rows}</tbody>
</table>

<div class="chart-wrap">
  <img src="data:image/png;base64,{chart_b64}" alt="Logro por asignatura">
  <div class="caption">Figura 1 — Porcentaje de logro promedio por asignatura</div>
</div>

</body>
</html>"""

# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    out = Path(__file__).parent / "output_weasyprint.pdf"
    print("Generando gráfico con matplotlib...")
    chart = bar_chart_png_b64()
    print("Construyendo HTML...")
    html = build_html(chart)
    print("Renderizando PDF con WeasyPrint...")
    from weasyprint import HTML
    HTML(string=html).write_pdf(str(out))
    print(f"✓ PDF generado: {out}")
