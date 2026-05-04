"""Steps de extracción de datos desde PDFs.

Hoy contiene `RunDIAPDFExtraction`, portado literal del script artesanal
`script_consolidar_DIA.py` que el cliente usó durante meses contra el
formato exacto de los PDFs de Agencia DIA. No reescribir las funciones
helper (camelot + fitz + análisis de píxeles) — están afinadas y
funcionan.

Ver `docs/desarrollo/script_dia_artesanal_referencia.md` para el plan
y mapeo línea-a-línea.
"""
from __future__ import annotations

import os
import re
from typing import List, Optional

import numpy as np
import pandas as pd

from .step import Step


# ─────────────────────────────────────────────────────────────────────────
# Helpers PDF (copiados literal del script_consolidar_DIA.py)
# ─────────────────────────────────────────────────────────────────────────

def _region_darkness(page, bbox, zoom: float = 5.0) -> float:
    """Renderiza bbox y devuelve oscuridad (1 - brillo medio).

    Usado para detectar la alternativa marcada en negrita: el texto en
    bold tiene más píxeles oscuros por unidad de área.
    """
    import fitz
    from PIL import Image

    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=bbox, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    gray = img.convert("L")
    arr = np.array(gray, dtype=np.float32)
    return 1.0 - arr.mean() / 255.0


def _extract_bold_alternatives(
    pdf_path: str,
    df_intermedio: pd.DataFrame,
    start_page: int = 0,
    end_page: Optional[int] = None,
    letter_tokens=("A:", "B:", "C:", "D:", "E:", "N:"),
    x_min: float = 450,
    zoom: float = 5.0,
) -> List[dict]:
    """Encuentra la alternativa correcta marcada en negrita por pregunta.

    Recorre los tokens A:/B:/C:/D:/E:/N: del PDF en orden de lectura
    (página → y), los asigna secuencialmente a las filas del df
    consumiendo tantos tokens como alternativas tenga cada pregunta:
        - A-D + N: 5 tokens
        - A-E + N: 6 tokens
        - RC (sólo N:): 1 token (se descarta, la respuesta sale directo
          de la celda).

    Devuelve una lista alineada con las filas NO-RC del df.
    """
    import fitz

    letter_set = set(letter_tokens)
    doc = fitz.open(pdf_path)
    if end_page is None:
        end_page = len(doc)

    # 1) Recolectar tokens en orden de lectura (page-major, luego por y)
    stream = []
    for pi in range(start_page, end_page):
        page = doc[pi]
        cand = [
            w for w in page.get_text("words")
            if w[4] in letter_set and w[0] >= x_min
        ]
        cand.sort(key=lambda w: w[1])
        for w in cand:
            stream.append((pi, w))

    def count_tokens(cell: str) -> int:
        return sum(
            1 for line in cell.split("\n")
            if line[:2] in ("A:", "B:", "C:", "D:", "E:", "N:")
        )

    results = []
    idx = 0
    for ri, row in df_intermedio.iterrows():
        cell = row.iloc[-1]
        n_tokens = count_tokens(cell)
        if idx + n_tokens > len(stream):
            raise RuntimeError(
                f"{pdf_path}: tokens insuficientes en el stream "
                f"(idx={idx}, need={n_tokens}, total={len(stream)}, fila df={ri})"
            )
        bundle = stream[idx:idx + n_tokens]
        idx += n_tokens

        if "RC" in cell:
            # La respuesta sale directo de la celda, no necesita scoring.
            continue

        # Score letras (ignorar N) y elegir la más oscura como correcta.
        scores = {}
        for pi, w in bundle:
            x0, y0, x1, y1, tok = w[:5]
            letter = tok[:-1]
            if letter == "N":
                continue
            d = _region_darkness(doc[pi], (x0, y0, x1, y1), zoom=zoom)
            scores[letter] = d
        winner = max(scores.items(), key=lambda kv: kv[1])[0]
        results.append({"winner": winner, "scores": scores})

    doc.close()
    return results


def _get_correct_percent(cell: str, correct: str) -> float:
    """Parsea celda 'A: 34.62%\\nB: 7.69%\\n...' y devuelve % de la correcta."""
    for line in cell.split("\n"):
        if line.startswith(correct):
            return float(line.split(": ")[1].replace("%", ""))
    return 0.0


def _detectar_paginas_tabla_preguntas(pdf_path: str) -> str:
    """Detecta el rango de páginas (1-indexado) de la sección
    'N. Resultados por pregunta' del informe DIA.

    El número de sección varía: en Matemáticas es '4. Resultados por
    pregunta' y en Lectura es '3. Resultados por pregunta'. Por eso
    matcheamos cualquier dígito al inicio. La sección termina en la
    página anterior a 'Resultados por estudiante'.

    Saltamos la página 1 porque contiene el índice ("En este informe
    encontrará: 1. ... N. Resultados por pregunta ...") que daría falso
    match.
    """
    import fitz

    doc = fitz.open(pdf_path)
    n = len(doc)
    start = None
    end = None
    pat_start = re.compile(r"\d+\.\s*Resultados\s+por\s+pregunta", re.IGNORECASE)
    pat_end = re.compile(r"\d+\.\s*Resultados\s+por\s+estudiante", re.IGNORECASE)
    for i in range(1, n):
        text = doc[i].get_text()
        if start is None and pat_start.search(text):
            start = i + 1
        elif start is not None and pat_end.search(text):
            end = i  # página anterior a 'Resultados por estudiante'
            break
    doc.close()
    if start is None:
        raise ValueError(f"No se halló 'Resultados por pregunta' en {pdf_path}")
    if end is None:
        end = n  # si no hay sección de cierre, hasta el final
    return f"{start}-{end}"


def _extraer_establecimiento_y_curso(pdf_path: str) -> tuple[str, str, dict]:
    """Extrae establecimiento, curso y mapa completo de etiquetas de la
    primera página del informe DIA.

    Usa la fecha (dd/mm/yyyy) como ancla para tomar las 7 líneas finales
    en el orden esperado.
    """
    import fitz

    doc = fitz.open(pdf_path)
    page = doc[0]

    blocks = page.get_text("dict")["blocks"]
    lineas = []
    for b in blocks:
        if "lines" in b:
            for ln in b["lines"]:
                txt = "".join(span["text"] for span in ln["spans"]).strip()
                if txt:
                    lineas.append(txt)

    etiquetas = [
        "Establecimiento:",
        "RBD:",
        "Nombre director o directora:",
        "Nombre docente de la asignatura:",
        "Curso:",
        "Cantidad de estudiantes que considera este informe:",
        "Fecha y hora de generación de este informe:",
    ]

    idx_fecha = None
    for i in range(len(lineas) - 1, -1, -1):
        if re.search(r"\d{2}/\d{2}/\d{4}", lineas[i]):
            idx_fecha = i
            break

    if idx_fecha is not None and idx_fecha >= len(etiquetas) - 1:
        valores = lineas[idx_fecha - (len(etiquetas) - 1): idx_fecha + 1]
    else:
        valores = lineas[-len(etiquetas):]

    mapa = dict(zip(etiquetas, valores))
    establecimiento = mapa.get("Establecimiento:")
    curso = mapa.get("Curso:")

    doc.close()
    return establecimiento, curso, mapa


# ─────────────────────────────────────────────────────────────────────────
# Step principal
# ─────────────────────────────────────────────────────────────────────────


class RunDIAPDFExtraction(Step):
    """Extrae el cuadro 'Resultados por pregunta' de los PDFs Agencia DIA.

    Para cada PDF en `ctx.inputs[input_key]`:
        1. Detecta automáticamente el rango de páginas de la sección.
        2. Extrae establecimiento y curso de la portada.
        3. Lee las tablas con camelot lattice (filtra impares).
        4. Normaliza columnas (Matemáticas trae 8, Lectura trae 6).
        5. Para preguntas de alternativas, detecta la respuesta correcta
           por análisis de píxeles (texto en negrita) y extrae el % de
           esa alternativa.
        6. Para preguntas de respuesta corta (RC), extrae el % directo.
        7. Limpia saltos de línea y normaliza capitalización del Eje
           Temático.

    Output (`ctx.artifacts[output_key]`): DataFrame con columnas
        ["N° Pregunta", "Eje Temático", "Habilidad",
         "Indicador de evaluación", "% respuestas", "Logro",
         "Establecimiento", "Curso"].

    Parámetros:
        input_key: clave en ctx.inputs con los PDFs a procesar.
        output_key: clave del artifact resultante (default
            "df_preguntas_pdf").

    Raises:
        ValueError: si un PDF no contiene la sección 'Resultados por
            pregunta'.
        RuntimeError: si el conteo de tokens A:/B:/C:/D:/E:/N: no
            coincide con las filas de la tabla.
    """

    def __init__(
        self,
        input_key: Optional[str] = None,
        output_key: Optional[str] = None,
    ):
        resolved_output_key = output_key or (
            f"df_preguntas_pdf" if not input_key else f"df_preguntas_{input_key}"
        )
        super().__init__(
            name="RunDIAPDFExtraction",
            requires=[input_key] if input_key else [],
            produces=[resolved_output_key] if resolved_output_key else [],
        )
        self.input_key = input_key
        self.output_key = resolved_output_key

    def _process_pdf(self, pdf_path: str) -> pd.DataFrame:
        """Procesa un PDF DIA y devuelve un df normalizado."""
        import camelot.io as camelot

        pages = _detectar_paginas_tabla_preguntas(pdf_path)
        self._log(f"  {pdf_path}: páginas {pages}")

        tablas = camelot.read_pdf(pdf_path, pages=pages, flavor="lattice")
        tablas_impares = [t for i, t in enumerate(tablas) if i % 2 == 1]

        establecimiento, curso, _ = _extraer_establecimiento_y_curso(pdf_path)

        df_intermedio = pd.concat(
            [t.df.iloc[1:] for t in tablas_impares], ignore_index=True
        )

        # Matemáticas trae 8 columnas (con N° OA, Nivel OA y N° OA del
        # grado actual) → drop 1, 2, 6. Lectura trae 6 (sin las dos extras
        # de OA) → drop solo 1.
        if df_intermedio.shape[1] == 8:
            df_intermedio = df_intermedio.drop(columns=[1, 2, 6]).reset_index(drop=True)
        elif df_intermedio.shape[1] == 6:
            df_intermedio = df_intermedio.drop(columns=[1]).reset_index(drop=True)
        df_intermedio.columns = list(range(df_intermedio.shape[1]))

        page_start, page_end = map(int, pages.split("-"))
        page_start -= 1  # 1-indexed inclusive → 0-indexed

        respuestas_correctas = _extract_bold_alternatives(
            pdf_path, df_intermedio,
            start_page=page_start, end_page=page_end, x_min=450,
        )

        i = 0
        for j, row in enumerate(df_intermedio.itertuples(index=False)):
            cell_pct = row[4]
            if "RC" in cell_pct:
                valores = cell_pct.split("RC:")
                rc = valores[1].split("\n")[0].strip()
                rc = float(rc.replace("%", "")) / 100
                df_intermedio.at[j, 5] = rc
            else:
                r_correcta = respuestas_correctas[i]["winner"]
                porcentaje = _get_correct_percent(cell_pct, r_correcta) / 100
                df_intermedio.at[j, 5] = porcentaje
                i += 1

        df_intermedio.at[:, 6] = establecimiento
        df_intermedio.at[:, 7] = curso

        return df_intermedio

    def run(self, ctx):
        before = self._snapshot_artifacts(ctx)

        input_key = self.input_key or ctx.params.get("input_key")
        if not input_key:
            raise ValueError(f"[{self.name}] No se pudo resolver input_key.")
        self.input_key = input_key
        output_key = self.output_key or f"df_preguntas_{input_key}"
        self.output_key = output_key

        archivos = ctx.inputs.get(input_key, [])
        pdfs = [str(f) for f in archivos if str(f).lower().endswith(".pdf")]
        if not pdfs:
            self._log(f"[{self.name}] Sin PDFs en '{input_key}'. Devuelve df vacío.")
            ctx.artifacts[output_key] = pd.DataFrame()
            ctx.last_artifact_key = output_key
            ctx.last_step = self.name
            self._log_artifacts_delta(ctx, before)
            return

        # Datos cargados por el usuario vía EnrichWithUserInput (Hito,
        # Asignatura, etc.) — se inyectan por archivo después del rename
        # de columnas (antes rompía el `df.columns = [...]` con length mismatch).
        user_inputs_store = getattr(ctx, "user_inputs", {}).get("enrich_per_file", {})

        # Nombres alineados con las dimensiones registradas en la métrica
        # DIA por Pregunta (id=7).
        BASE_COLS = [
            "N Pregunta", "Eje Temático", "Habilidad",
            "Indicador", "% respuestas", "Logro",
            "Establecimiento", "Curso",
        ]

        rendered_dfs: List[pd.DataFrame] = []
        for pdf in pdfs:
            try:
                df_pdf = self._process_pdf(pdf)
                # 1. Renombrar columnas posicionales (las 8 estándar)
                df_pdf.columns = BASE_COLS
                # 2. Limpiar saltos de línea / capitalizar
                for col in ("Eje Temático", "Habilidad", "Indicador", "% respuestas"):
                    df_pdf[col] = (
                        df_pdf[col]
                        .astype(str)
                        .str.replace("-\n", "", regex=False)
                        .str.replace("\n", "", regex=False)
                        .str.strip()
                    )
                df_pdf["Eje Temático"] = (
                    df_pdf["Eje Temático"]
                    .str.title()
                    .str.replace(" Y ", " y ", regex=False)
                )
                # 3. Inyectar user_inputs específicos de este PDF (Hito, Asignatura)
                fname = os.path.basename(pdf)
                for col, val in user_inputs_store.get(fname, {}).items():
                    df_pdf[col] = val
                rendered_dfs.append(df_pdf)
            except Exception as e:
                self._log(f"[{self.name}] Error procesando {pdf}: {e}")
                raise

        resultados = pd.concat(rendered_dfs, ignore_index=True) if rendered_dfs else pd.DataFrame()

        ctx.artifacts[output_key] = resultados
        ctx.last_artifact_key = output_key
        ctx.last_step = self.name
        self._log_artifacts_delta(ctx, before)
