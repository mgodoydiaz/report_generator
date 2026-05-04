// Spike PDF — Typst
// Informe de resultados PDL — 4° Básico · 2024

#set document(title: "Informe PDL 2024", author: "Fundación PHP")
#set page(
  paper: "a4",
  margin: (top: 2cm, bottom: 2cm, left: 2.2cm, right: 2.2cm),
  footer: context [
    #set text(size: 7.5pt, fill: luma(150))
    #align(right)[Fundación PHP · Evaluación 2024 · Pág. #counter(page).display()]
  ],
)
#set text(font: "DejaVu Serif", size: 10pt, fill: rgb("#1e293b"))
#set par(leading: 0.75em)

// ── Colores ──────────────────────────────────────────────────────────────────

#let indigo    = rgb("#4f46e5")
#let indigo-lt = rgb("#e0e7ff")
#let cyan      = rgb("#06b6d4")
#let slate-mid = rgb("#64748b")
#let slate-lt  = rgb("#f1f5f9")
#let green-bg  = rgb("#dcfce7")
#let yellow-bg = rgb("#fef9c3")
#let red-bg    = rgb("#fee2e2")

// ── PORTADA ──────────────────────────────────────────────────────────────────

#page[
  #v(5cm)

  #align(center)[
    #line(length: 60%, stroke: 5pt + indigo)
    #v(0.5cm)
    #text(size: 28pt, weight: "bold", fill: indigo)[Informe de Resultados]
    #v(0.3cm)
    #text(size: 13pt, fill: slate-mid)[Evaluación PDL — 4° Básico · 2024]
    #v(0.8cm)
    #text(size: 9pt, fill: slate-mid)[
      Establecimiento: Colegio Demo S/N \
      Fecha de generación: 20 de abril de 2026 \
      Generado con *Typst 0.14*
    ]
    #v(0.5cm)
    #line(length: 60%, stroke: 5pt + cyan)
  ]
]

// ── PÁGINA 2 ─────────────────────────────────────────────────────────────────

#v(0.2cm)
#text(size: 14pt, weight: "bold", fill: indigo)[Resumen de resultados]
#line(length: 100%, stroke: 1.5pt + indigo-lt)
#v(0.3cm)

La siguiente tabla muestra el desempeño individual de los estudiantes evaluados en
la prueba PDL aplicada durante el primer semestre de 2024. Los niveles de logro se
clasifican en *Alto* (≥70), *Medio* (50–69) y *Bajo* (inferior a 50).

#v(0.4cm)

// ── TABLA ─────────────────────────────────────────────────────────────────────

#let nivel-color(nv) = {
  if nv == "Alto"  { green-bg  }
  else if nv == "Medio" { yellow-bg }
  else { red-bg }
}

#let estudiantes = (
  ("García, Valentina",  "4°A", "74", "Alto"),
  ("Muñoz, Sebastián",   "4°A", "58", "Medio"),
  ("López, Camila",      "4°B", "81", "Alto"),
  ("Rojas, Diego",       "4°B", "43", "Bajo"),
  ("Herrera, Isidora",   "4°A", "67", "Medio"),
  ("Soto, Matías",       "4°B", "55", "Medio"),
)

#table(
  columns: (1fr, 2.5cm, 2.5cm, 3cm),
  fill: (col, row) => {
    if row == 0 { indigo }
    else if col == 3 {
      nivel-color(estudiantes.at(row - 1).at(3))
    } else if calc.odd(row) { white }
    else { slate-lt }
  },
  stroke: 0.5pt + rgb("#e2e8f0"),
  inset: 7pt,

  // Header
  table.header(
    text(fill: white, weight: "bold")[Estudiante],
    text(fill: white, weight: "bold")[Curso],
    text(fill: white, weight: "bold", align(center)[Puntaje]),
    text(fill: white, weight: "bold", align(center)[Nivel]),
  ),

  // Filas
  ..estudiantes.map(((nombre, curso, puntaje, nivel)) => (
    nombre,
    curso,
    align(center)[#puntaje],
    align(center)[#nivel],
  )).flatten()
)

// ── GRÁFICO (barras nativas Typst) ───────────────────────────────────────────

#v(0.7cm)
#text(size: 11pt, weight: "bold")[Logro por asignatura — 4° básico]
#v(0.3cm)

#let asig    = ("Lenguaje", "Matemática", "Ciencias", "Historia")
#let valores = (62, 54, 71, 48)
#let colores-bar = (rgb("#6366f1"), rgb("#8b5cf6"), rgb("#06b6d4"), rgb("#f59e0b"))
#let bar-w   = 2.5cm
#let max-h   = 5cm

#block(width: 100%)[
  #stack(dir: ltr, spacing: 0.6cm,
    ..asig.zip(valores).zip(colores-bar).map((((name, val), col)) => {
      let h = max-h * val / 100
      stack(dir: ttb, spacing: 4pt,
        align(center)[#text(size: 8pt, weight: "bold")[#val%]],
        rect(width: bar-w, height: h, fill: col, radius: 3pt),
        align(center)[#text(size: 8pt, fill: slate-mid)[#name]],
      )
    })
  )
]

#v(0.2cm)
#align(center)[
  #text(size: 8pt, fill: slate-mid)[
    _Figura 1 — Porcentaje de logro promedio por asignatura_
  ]
]
