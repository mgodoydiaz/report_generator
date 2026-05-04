"""
Spike PDF — ReportLab
Genera un informe de ejemplo con: portada, tabla de resultados y gráfico (matplotlib PNG).
"""

import io
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ── Paleta ───────────────────────────────────────────────────────────────────

INDIGO     = colors.HexColor("#4f46e5")
INDIGO_LIGHT = colors.HexColor("#e0e7ff")
CYAN       = colors.HexColor("#06b6d4")
SLATE_DARK = colors.HexColor("#1e293b")
SLATE_MID  = colors.HexColor("#64748b")
SLATE_LIGHT= colors.HexColor("#f1f5f9")
GREEN_BG   = colors.HexColor("#dcfce7")
YELLOW_BG  = colors.HexColor("#fef9c3")
RED_BG     = colors.HexColor("#fee2e2")

# ── Gráfico matplotlib ───────────────────────────────────────────────────────

def bar_chart_image():
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
    return buf

# ── Estilos ──────────────────────────────────────────────────────────────────

def make_styles():
    base = getSampleStyleSheet()
    styles = {}
    styles["cover_title"] = ParagraphStyle(
        "cover_title", parent=base["Title"],
        fontSize=28, textColor=INDIGO, spaceAfter=10, alignment=TA_CENTER,
    )
    styles["cover_sub"] = ParagraphStyle(
        "cover_sub", parent=base["Normal"],
        fontSize=13, textColor=SLATE_MID, spaceAfter=8, alignment=TA_CENTER,
    )
    styles["cover_meta"] = ParagraphStyle(
        "cover_meta", parent=base["Normal"],
        fontSize=9, textColor=SLATE_MID, leading=16, alignment=TA_CENTER,
    )
    styles["h2"] = ParagraphStyle(
        "h2", parent=base["Heading2"],
        fontSize=14, textColor=INDIGO, spaceBefore=18, spaceAfter=6,
    )
    styles["body"] = ParagraphStyle(
        "body", parent=base["Normal"],
        fontSize=10, leading=15, textColor=SLATE_DARK,
    )
    styles["caption"] = ParagraphStyle(
        "caption", parent=base["Normal"],
        fontSize=8, textColor=SLATE_MID, alignment=TA_CENTER, spaceBefore=4,
    )
    return styles

# ── Footer/header via canvas ─────────────────────────────────────────────────

def on_later_pages(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(SLATE_MID)
    canvas.drawRightString(A4[0] - 2*cm, 1.2*cm, f"Fundación PHP · Evaluación 2024 · Pág. {doc.page}")
    canvas.restoreState()

# ── Datos ────────────────────────────────────────────────────────────────────

ESTUDIANTES = [
    ("García, Valentina",  "4°A", 74, "Alto"),
    ("Muñoz, Sebastián",   "4°A", 58, "Medio"),
    ("López, Camila",      "4°B", 81, "Alto"),
    ("Rojas, Diego",       "4°B", 43, "Bajo"),
    ("Herrera, Isidora",   "4°A", 67, "Medio"),
    ("Soto, Matías",       "4°B", 55, "Medio"),
]

NIVEL_BG = {"Alto": GREEN_BG, "Medio": YELLOW_BG, "Bajo": RED_BG}

# ── Construcción del documento ────────────────────────────────────────────────

def build_story(styles, chart_buf):
    story = []

    # ── PORTADA ──
    story.append(Spacer(1, 6*cm))
    story.append(HRFlowable(width="60%", thickness=5, color=INDIGO,
                             hAlign="CENTER", spaceAfter=18))
    story.append(Paragraph("Informe de Resultados", styles["cover_title"]))
    story.append(Paragraph("Evaluación PDL — 4° Básico · 2024", styles["cover_sub"]))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        "Establecimiento: Colegio Demo S/N<br/>"
        "Fecha de generación: 20 de abril de 2026<br/>"
        "Generado con <b>ReportLab 4</b>",
        styles["cover_meta"]
    ))
    story.append(HRFlowable(width="60%", thickness=5, color=CYAN,
                             hAlign="CENTER", spaceBefore=18))

    # ── PÁGINA 2 ──
    story.append(PageBreak())

    story.append(Paragraph("Resumen de resultados", styles["h2"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=INDIGO_LIGHT, spaceAfter=8))
    story.append(Paragraph(
        "La siguiente tabla muestra el desempeño individual de los estudiantes evaluados "
        "en la prueba PDL aplicada durante el primer semestre de 2024. Los niveles de logro "
        "se clasifican en <b>Alto</b> (≥70), <b>Medio</b> (50–69) y <b>Bajo</b> (&lt;50).",
        styles["body"]
    ))
    story.append(Spacer(1, 0.4*cm))

    # Tabla
    header = ["Estudiante", "Curso", "Puntaje", "Nivel"]
    data = [header] + [[n, c, str(p), nv] for n, c, p, nv in ESTUDIANTES]
    col_widths = [7*cm, 2.5*cm, 2.5*cm, 3*cm]
    t = Table(data, colWidths=col_widths)

    row_styles = [
        ("BACKGROUND",   (0, 0), (-1, 0), INDIGO),
        ("TEXTCOLOR",    (0, 0), (-1, 0), colors.white),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, -1), 9),
        ("ALIGN",        (2, 0), (3, -1), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SLATE_LIGHT]),
        ("GRID",         (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ("TOPPADDING",   (0, 0), (-1, -1), 6),
        ("LEFTPADDING",  (0, 0), (-1, -1), 8),
    ]
    # Color de nivel por fila
    for i, (_, _, _, nivel) in enumerate(ESTUDIANTES, start=1):
        bg = NIVEL_BG.get(nivel, colors.white)
        row_styles.append(("BACKGROUND", (3, i), (3, i), bg))

    t.setStyle(TableStyle(row_styles))
    story.append(t)

    # Gráfico
    story.append(Spacer(1, 0.6*cm))
    img = Image(chart_buf, width=13*cm, height=6.5*cm)
    img.hAlign = "CENTER"
    story.append(img)
    story.append(Paragraph(
        "Figura 1 — Porcentaje de logro promedio por asignatura", styles["caption"]
    ))

    return story

# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    out = Path(__file__).parent / "output_reportlab.pdf"
    print("Generando gráfico con matplotlib...")
    chart_buf = bar_chart_image()
    print("Construyendo estilos y story...")
    styles = make_styles()
    story = build_story(styles, chart_buf)
    print("Renderizando PDF con ReportLab...")
    doc = SimpleDocTemplate(
        str(out), pagesize=A4,
        leftMargin=2.2*cm, rightMargin=2.2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )
    doc.build(story, onLaterPages=on_later_pages)
    print(f"✓ PDF generado: {out}")
