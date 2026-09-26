# -*- coding: utf-8 -*-
"""
dia_1basico_items.py
=====================
Completa los ítems 7-16 de Lectura 1° básico DIA, que el pipeline actual
(`RunDIAPDFExtraction`, `backend/rgenerator/core/pdf_steps.py`) NO extrae.

Contexto (confirmado sept-2026, ver `/mnt/c/.../diagnostico/04_items_1basico.md`):
En 1° básico, el informe PDF de Lectura "monitoreo" (Diagnóstico/Intermedio)
solo tabula Comprensión oral (preguntas 1-6 y 17-22) en la "Tabla 1. Resultados
del curso en cada pregunta de Comprensión oral". Las áreas Conciencia
fonológica, Principio alfabético y Lectura de palabras (preguntas 7-16, por
supuesto de numeración — el PDF no las tabula ni las numera) aparecen SOLO
como gráficos (páginas 3-5, Gráficos 2/3/4) sin valores numéricos en texto:
no hay forma de validarlas cruzando contra el PDF más que el orden y el
nombre de cada subhabilidad (que sí coincide, ver "Definiciones" en esas
páginas).

Ese bloque sí está en el XLS de estudiantes de cada curso (columna por
subhabilidad, valores 'L'/'NL' por estudiante), header en la fila 13
(`header_row=12`, igual que `RunExcelETL`), Establecimiento en B5 y Curso en
B6. Las 10 columnas — en este orden fijo, confirmado contra las páginas 3-5
del PDF — son:

    Conciencia fonológica:  Sílaba inicial, Sílaba final, Sonido inicial, Sonido final
    Principio alfabético:   Vocales A, E, U | Cons. M, L, P, S | Cons. D, T, N, R
    Lectura de palabras:    Sílaba directa, Sílaba indirecta, Sílaba compleja

Criterio de logro (acordado con Miguel): L=1, NL=0 en escala 0-1. Logro del
ítem = proporción de estudiantes con L entre quienes tienen L o NL (values
vacíos/ausentes se ignoran y se reportan).

Los XLS de Cierre de 1° básico usan OTRO formato ('Lectura de palabras',
'Lectura de oraciones', 'Comprensión lectora' con %) — quedan FUERA de este
script. Se detectan por firma de columnas y se saltan con aviso.

Formato de salida: exactamente las mismas columnas que produce
`RunDIAPDFExtraction` para Comprensión oral (BASE_COLS en pdf_steps.py) más
Hito/Asignatura/Año, de modo que el CSV se pueda concatenar con
`preguntas_raw` y pasar por el mismo `ApplyDerivedFields` (lookup_range
mapping_id 35, lookup_dict mapping_id 36) + `SaveToMetric` metric_id 7.

Modo de uso (solo genera archivos, NUNCA escribe en ninguna DB):
    python scripts/dia_1basico_items.py \
        --xls "/ruta/a/carpeta/o/archivo.xls" \
        --out ./out_dir
        [--hito INTERMEDIO] [--anio 2026]

--dry-run está SIEMPRE activo (no existe modo de carga real en este script;
la carga a metric_data queda para una etapa posterior, manual o vía step).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

# ─────────────────────────────────────────────────────────────────────────
# Constantes de dominio
# ─────────────────────────────────────────────────────────────────────────

#: Mismas columnas que RunDIAPDFExtraction (pdf_steps.py, BASE_COLS) para
#: que el resultado se pueda concatenar con preguntas_raw / preguntas_pdf.
BASE_COLS = [
    "N Pregunta", "Eje Temático", "Habilidad",
    "Indicador", "% respuestas", "Logro",
    "Establecimiento", "Curso",
]

#: (columna XLS, Eje Temático, Habilidad legible, N Pregunta, Indicador)
#: Orden y numeración 7-16: SUPUESTO acordado con Miguel (el PDF no numera
#: estas preguntas). Validado solo en ORDEN y NOMBRE contra las páginas 3-5
#: del PDF (Gráficos 2/3/4 + "Definiciones"); el PDF no expone los
#: porcentajes de estos gráficos como texto, así que no se pudo
#: contrastar el valor numérico de Logro contra el informe.
ITEMS_1BASICO = [
    {
        "col_xls": "Sílaba inicial",
        "eje": "Conciencia Fonológica",
        "habilidad": "Sílaba inicial",
        "n_pregunta": "7",
        "indicador": (
            "Habilidad para reconocer y aislar la sílaba inicial de una "
            "palabra al escucharla."
        ),
    },
    {
        "col_xls": "Sílaba final",
        "eje": "Conciencia Fonológica",
        "habilidad": "Sílaba final",
        "n_pregunta": "8",
        "indicador": (
            "Habilidad para reconocer y aislar la sílaba final de una "
            "palabra al escucharla."
        ),
    },
    {
        "col_xls": "Sonido inicial",
        "eje": "Conciencia Fonológica",
        "habilidad": "Sonido inicial",
        "n_pregunta": "9",
        "indicador": (
            "Habilidad para identificar y aislar el primer sonido (fonema) "
            "que se escucha al pronunciar una palabra."
        ),
    },
    {
        "col_xls": "Sonido final",
        "eje": "Conciencia Fonológica",
        "habilidad": "Sonido final",
        "n_pregunta": "10",
        "indicador": (
            "Habilidad para identificar y aislar el último sonido (fonema) "
            "que se escucha al pronunciar una palabra."
        ),
    },
    {
        # XLS trae espacios irregulares: "Vocales     A, E, U"
        "col_xls_regex": r"^vocales\s+a,\s*e,\s*u$",
        "eje": "Principio Alfabético",
        "habilidad": "Vocales A, E, U",
        "n_pregunta": "11",
        "indicador": (
            "Reconocimiento y asociación de los fonemas vocálicos (A, E, U) "
            "con su grafema."
        ),
    },
    {
        "col_xls_regex": r"^cons\.\s+m,\s*l,\s*p,\s*s$",
        "eje": "Principio Alfabético",
        "habilidad": "Cons. M, L, P, S",
        "n_pregunta": "12",
        "indicador": (
            "Reconocimiento y asociación de las consonantes de alta "
            "frecuencia (M, L, P, S) con su grafema."
        ),
    },
    {
        "col_xls_regex": r"^cons\.\s+d,\s*t,\s*n,\s*r$",
        "eje": "Principio Alfabético",
        "habilidad": "Cons. D, T, N, R",
        "n_pregunta": "13",
        "indicador": (
            "Reconocimiento y asociación de las consonantes de dificultad "
            "articulatoria intermedia (D, T, N, R) con su grafema."
        ),
    },
    {
        "col_xls": "Sílaba directa",
        "eje": "Lectura de Palabras",
        "habilidad": "Sílaba directa",
        "n_pregunta": "14",
        "indicador": (
            "Lectura de palabras con combinación consonante-vocal (CV), "
            "ej. ca-sa, me-sa."
        ),
    },
    {
        "col_xls": "Sílaba indirecta",
        "eje": "Lectura de Palabras",
        "habilidad": "Sílaba indirecta",
        "n_pregunta": "15",
        "indicador": (
            "Lectura de palabras con combinación vocal-consonante (VC), "
            "ej. es-pi-na, an-tor-cha."
        ),
    },
    {
        "col_xls": "Sílaba compleja",
        "eje": "Lectura de Palabras",
        "habilidad": "Sílaba compleja",
        "n_pregunta": "16",
        "indicador": (
            "Lectura de palabras con combinación consonante-vocal-"
            "consonante (CVC), ej. car-ta, pal-ta."
        ),
    },
]

#: Firma de columnas de los XLS de Cierre 1° básico (otro formato, fuera
#: de alcance de este script).
COLUMNAS_CIERRE = {"Lectura de palabras", "Lectura de oraciones", "Comprensión lectora"}

#: dimension_id (metric 7, "Resultados DIA por Pregunta") — igual que en prod.
DIM_IDS = {
    "Establecimiento": "3",
    "Año": "4",
    "Curso": "5",
    "Asignatura": "8",
    "Habilidad": "12",
    "Eje Temático": "13",
    "Hito": "14",
    "Nivel": "15",
    "N Pregunta": "16",
    "Indicador": "18",
}

#: Umbrales Nivel Logro (igual que mapping_id 35 / apply_lookup_range en prod).
UMBRALES_NIVEL_LOGRO = [
    (0.4, "Inicial"),
    (0.6, "Intermedio"),
]
NIVEL_LOGRO_DEFAULT = "Avanzado"

#: Mapeo Establecimiento canónico por carpeta raíz / RBD (ver
#: scripts/dia_establecimiento_canonico.py y
#: diagnostico/prod_dia_cargado.txt). El XLS de "BÁSICA" (RBD 16843) trae
#: en la celda B5 el nombre institucional largo del Liceo de Panguipulli
#: (bug de exportación de la Agencia DIA / dato mal cargado en su
#: plataforma para este RBD) — NO corresponde al establecimiento real.
#: Por eso NO se usa la celda B5 para 1° básico: se deriva del nombre de
#: carpeta / RBD, igual que hace el equipo para el resto de las cargas.
ESTABLECIMIENTO_POR_CARPETA = {
    "BASICA": "Colegio Básico",
    "BÁSICA": "Colegio Básico",
    "PANGUIPULLI": "Liceo PHP Panguipulli",
    "PULLINQUE": "Liceo PHP Pullinque",
}


@dataclass
class ArchivoDetectado:
    path: Path
    hito: Optional[str]
    anio: Optional[str]
    establecimiento: Optional[str]
    avisos: list


# ─────────────────────────────────────────────────────────────────────────
# Inferencia de metadatos desde ruta / nombre de archivo
# ─────────────────────────────────────────────────────────────────────────

def _normaliza_carpeta(nombre: str) -> str:
    return nombre.strip().upper()


def inferir_establecimiento(path: Path) -> Optional[str]:
    """Deriva el establecimiento canónico de la ruta (carpeta COLEGIO/AÑO/HITO/...).

    Ver nota en ESTABLECIMIENTO_POR_CARPETA: NO se usa el valor de la
    celda B5 del XLS para este curso, porque en los archivos de 1° básico
    (RBD 16843, carpeta BÁSICA) esa celda trae el nombre largo del Liceo
    de Panguipulli por un problema de datos ajeno a este script.
    """
    for parte in path.parts:
        clave = _normaliza_carpeta(parte)
        if clave in ESTABLECIMIENTO_POR_CARPETA:
            return ESTABLECIMIENTO_POR_CARPETA[clave]
    return None


def inferir_hito_y_anio(path: Path) -> tuple[Optional[str], Optional[str], list]:
    """Infiere Hito y Año de la carpeta/nombre de archivo.

    - Año: primera carpeta numérica de 4 dígitos en la ruta, si no,
      4 dígitos en el nombre del archivo.
    - Hito: nombre de carpeta tipo "01 - DIAGNÓSTICO"/"02 - INTERMEDIO"/
      "03 - CIERRE". El nombre de archivo dice "monitoreo" tanto para
      Diagnóstico como Intermedio (ambigüedad de la Agencia DIA) — por
      eso el hito se toma SIEMPRE de la carpeta, nunca del nombre de
      archivo, y se avisa si no hay carpeta reconocible.
    """
    avisos = []
    anio = None
    for parte in path.parts:
        m = re.fullmatch(r"(20\d{2})", parte.strip())
        if m:
            anio = m.group(1)
            break
    if anio is None:
        m = re.search(r"(20\d{2})", path.name)
        if m:
            anio = m.group(1)
            avisos.append(f"Año inferido del nombre de archivo (no de carpeta): {anio}")

    hito = None
    for parte in path.parts:
        p = _normaliza_carpeta(parte)
        if "DIAGN" in p:
            hito = "DIAGNOSTICO"
            break
        if "INTERMEDIO" in p:
            hito = "INTERMEDIO"
            break
        if "CIERRE" in p:
            hito = "CIERRE"
            break
    if hito is None:
        if "cierre" in path.name.lower():
            hito = "CIERRE"
        elif "monitoreo" in path.name.lower() or "diagnostico" in path.name.lower():
            avisos.append(
                "No se encontró carpeta de hito reconocible (01-DIAGNÓSTICO/"
                "02-INTERMEDIO/03-CIERRE); no se pudo inferir Hito de forma "
                "no ambigua desde el nombre de archivo ('monitoreo' se usa "
                "para Diagnóstico e Intermedio por igual)."
            )
    elif hito == "DIAGNOSTICO" and "monitoreo" in path.name.lower() and "diagnostico" not in path.name.lower():
        avisos.append(
            "La carpeta dice DIAGNÓSTICO pero el archivo se llama "
            "'...monitoreo...' (no '...diagnostico...'): posible archivo "
            "mal archivado (ver caso confirmado BÁSICA/2026 1° básico "
            "Lectura, donde la copia en '01 - DIAGNÓSTICO' es la misma "
            "descarga que '02 - INTERMEDIO')."
        )
    return hito, anio, avisos


def hito_coincide_con_nombre(path: Path, hito: Optional[str]) -> bool:
    """True si el Hito (de carpeta) es consistente con la palabra clave del
    nombre de archivo ('diagnostico' / 'monitoreo' / 'cierre'). Se usa para
    decidir, entre dos archivos con contenido idéntico, cuál conservar."""
    nombre = path.name.lower()
    if hito == "DIAGNOSTICO":
        return "diagnostico" in nombre
    if hito == "INTERMEDIO":
        return "monitoreo" in nombre
    if hito == "CIERRE":
        return "cierre" in nombre
    return False


# ─────────────────────────────────────────────────────────────────────────
# Lectura y validación del XLS
# ─────────────────────────────────────────────────────────────────────────

def leer_xls_1basico(path: Path, header_row: int = 12) -> tuple[pd.DataFrame, str, str]:
    """Lee el XLS crudo (sin header) y devuelve (df_estudiantes, establecimiento_b5, curso).

    establecimiento_b5 es el valor LITERAL de B5 (solo informativo / para
    el reporte de discrepancias) — no se usa como Establecimiento final,
    ver `inferir_establecimiento`.
    """
    engine = "xlrd" if path.suffix.lower() == ".xls" else None
    raw = pd.read_excel(path, header=None, engine=engine)
    establecimiento_b5 = str(raw.iat[4, 1]).strip()
    curso = str(raw.iat[5, 1]).strip()
    df = pd.read_excel(path, header=header_row, engine=engine)
    df = df.dropna(how="all")
    return df, establecimiento_b5, curso


def es_formato_cierre_1basico(df: pd.DataFrame) -> bool:
    """True si las columnas del XLS calzan con el formato de Cierre (%),
    que no cubre este script."""
    cols = set(str(c).strip() for c in df.columns)
    return bool(COLUMNAS_CIERRE & cols)


def es_formato_lectura_monitoreo_1basico(df: pd.DataFrame) -> bool:
    """True si el XLS trae las 10 columnas L/NL de Lectura 1° básico
    monitoreo (Diagnóstico/Intermedio). Otros ramos (ej. Matemática 1°
    básico: 'Números y operaciones', 'Patrones y álgebra', ...) o Lectura
    de otros cursos no calzan y se saltean sin error."""
    encontradas = sum(1 for item in ITEMS_1BASICO if _resolver_columna(df, item) is not None)
    return encontradas == len(ITEMS_1BASICO)


def _resolver_columna(df: pd.DataFrame, item: dict) -> Optional[str]:
    """Encuentra la columna real del XLS para un ítem, normalizando espacios."""
    if "col_xls" in item:
        objetivo = item["col_xls"].strip().lower()
        for c in df.columns:
            if re.sub(r"\s+", " ", str(c)).strip().lower() == objetivo:
                return c
        return None
    patron = re.compile(item["col_xls_regex"])
    for c in df.columns:
        normalizado = re.sub(r"\s+", " ", str(c)).strip().lower()
        if patron.match(normalizado):
            return c
    return None


# ─────────────────────────────────────────────────────────────────────────
# Función pura: extracción de los 10 ítems
# ─────────────────────────────────────────────────────────────────────────

def extraer_items_1basico(
    df_estudiantes: pd.DataFrame,
    establecimiento: str,
    curso: str,
    hito: str,
    asignatura: str = "LECTURA",
    anio: Optional[str] = None,
) -> pd.DataFrame:
    """Calcula Logro por ítem (7-16) de Lectura 1° básico desde el XLS de
    estudiantes (columnas L/NL por subhabilidad).

    Logro = proporción de estudiantes con 'L' entre quienes tienen 'L' o
    'NL' (se ignoran vacíos/valores no reconocidos; se reporta cuántos).

    Devuelve un DataFrame con las columnas BASE_COLS (+ Hito/Asignatura/Año),
    una fila por ítem (10 filas), en el mismo formato que produce
    `RunDIAPDFExtraction` para que se pueda concatenar con `preguntas_raw`.

    Es una función PURA (no toca disco, no imprime): reutilizable como
    step de pipeline más adelante.
    """
    filas = []
    for item in ITEMS_1BASICO:
        col = _resolver_columna(df_estudiantes, item)
        if col is None:
            raise KeyError(
                f"No se encontró la columna del XLS para el ítem "
                f"'{item['habilidad']}' (N Pregunta {item['n_pregunta']}). "
                f"Columnas disponibles: {list(df_estudiantes.columns)}"
            )
        valores = df_estudiantes[col].astype(str).str.strip().str.upper()
        n_l = int((valores == "L").sum())
        n_nl = int((valores == "NL").sum())
        n_total_validos = n_l + n_nl
        n_ignorados = len(valores) - n_total_validos
        logro = (n_l / n_total_validos) if n_total_validos > 0 else float("nan")

        filas.append({
            "N Pregunta": item["n_pregunta"],
            "Eje Temático": item["eje"],
            "Habilidad": item["habilidad"],
            "Indicador": item["indicador"],
            "% respuestas": "",
            "Logro": logro,
            "Establecimiento": establecimiento,
            "Curso": curso,
            "Hito": hito,
            "Asignatura": asignatura,
            "Año": anio,
            "Nivel": nivel_por_curso(curso),
            # Metadatos auxiliares de trazabilidad (no forman parte de
            # BASE_COLS, se descartan al guardar el CSV final si molestan
            # en el pipeline, pero ayudan al diagnóstico).
            "_n_estudiantes_L": n_l,
            "_n_estudiantes_NL": n_nl,
            "_n_estudiantes_ignorados": n_ignorados,
        })
    return pd.DataFrame(filas)


def nivel_logro(logro: float) -> Optional[str]:
    """Replica lookup_range mapping_id 35 (left_inclusive: v <= max)."""
    if logro is None or (isinstance(logro, float) and pd.isna(logro)):
        return None
    for maximo, label in UMBRALES_NIVEL_LOGRO:
        if logro <= maximo:
            return label
    return NIVEL_LOGRO_DEFAULT


def nivel_por_curso(curso: str) -> str:
    """Replica lookup_dict mapping_id 36 para 1° básico: siempre 'Primeros'."""
    return "Primeros"


# ─────────────────────────────────────────────────────────────────────────
# Construcción del JSON metric_data (formato listo-para-insertar)
# ─────────────────────────────────────────────────────────────────────────

def construir_metric7_json(df_items: pd.DataFrame) -> list:
    registros = []
    for _, row in df_items.iterrows():
        dims = {}
        for col, dim_id in DIM_IDS.items():
            valor = row.get(col)
            if valor is None or (isinstance(valor, float) and pd.isna(valor)):
                continue
            dims[dim_id] = str(valor)
        logro = row["Logro"]
        value = {
            "Logro": None if pd.isna(logro) else round(float(logro), 4),
            "Nivel Logro": nivel_logro(logro),
        }
        registros.append({"dimensions_json": dims, "value": value})
    return registros


# ─────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────

def _buscar_xls(ruta: Path) -> list:
    if ruta.is_file():
        return [ruta]
    return sorted(
        p for p in ruta.rglob("*")
        if p.suffix.lower() in (".xls", ".xlsx") and not p.name.startswith("~$")
    )


def procesar_archivo(
    path: Path,
    hito_cli: Optional[str],
    anio_cli: Optional[str],
) -> tuple[Optional[pd.DataFrame], list, dict]:
    """Procesa un XLS. Devuelve (df_items|None, avisos, resumen_fila)."""
    avisos = []
    resumen = {"archivo": str(path)}

    df_raw, establecimiento_b5, curso = leer_xls_1basico(path)

    if curso.strip().upper().split(" ")[0] not in ("1", "1°", "1RO"):
        avisos.append(f"Curso '{curso}' no es 1° básico: archivo salteado.")
        return None, avisos, resumen

    if es_formato_cierre_1basico(df_raw):
        avisos.append(
            "Formato de Cierre (Lectura de palabras/oraciones/Comprensión "
            "lectora, con %) detectado — fuera de alcance de este script, "
            "se saltea."
        )
        return None, avisos, resumen

    if not es_formato_lectura_monitoreo_1basico(df_raw):
        avisos.append(
            "No trae las 10 columnas L/NL de Lectura 1° básico monitoreo "
            f"(columnas encontradas: {list(df_raw.columns)}) — no es un XLS "
            "de Lectura Diagnóstico/Intermedio, se saltea (ej. Matemática "
            "1° básico usa otro formato, fuera de alcance de este script)."
        )
        return None, avisos, resumen

    hito_inferido, anio_inferido, avisos_meta = inferir_hito_y_anio(path)
    avisos.extend(avisos_meta)
    hito = hito_cli or hito_inferido
    anio = anio_cli or anio_inferido
    if not hito:
        avisos.append("No se pudo determinar Hito: archivo salteado.")
        return None, avisos, resumen
    if hito == "CIERRE":
        avisos.append("Hito CIERRE detectado por ruta pero XLS no es formato Cierre; se revisa igual, avisar a Miguel.")

    establecimiento = inferir_establecimiento(path)
    if not establecimiento:
        avisos.append(
            f"No se pudo derivar Establecimiento canónico de la ruta; se usa "
            f"el valor crudo de B5 ('{establecimiento_b5}')."
        )
        establecimiento = establecimiento_b5
    elif establecimiento_b5 and "PANGUIPULLI" in establecimiento_b5.upper() and establecimiento != "Liceo PHP Panguipulli":
        avisos.append(
            f"B5 dice '{establecimiento_b5}' pero por carpeta/RBD se usa "
            f"Establecimiento='{establecimiento}' (ver nota "
            f"ESTABLECIMIENTO_POR_CARPETA en este script)."
        )

    df_items = extraer_items_1basico(
        df_raw, establecimiento=establecimiento, curso=curso,
        hito=hito, asignatura="LECTURA", anio=anio,
    )

    resumen.update({
        "curso": curso,
        "hito": hito,
        "anio": anio,
        "establecimiento": establecimiento,
        "n_estudiantes": len(df_raw),
        "logro_por_item": {
            row["N Pregunta"]: round(row["Logro"], 4) if pd.notna(row["Logro"]) else None
            for _, row in df_items.iterrows()
        },
    })
    return df_items, avisos, resumen


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--xls", required=True, help="Archivo .xls o carpeta (recursivo).")
    ap.add_argument("--hito", default=None, help="DIAGNOSTICO|INTERMEDIO|CIERRE (si no, se infiere).")
    ap.add_argument("--anio", default=None, help="Año (si no, se infiere).")
    ap.add_argument("--out", required=True, help="Carpeta de salida.")
    ap.add_argument(
        "--dry-run", action="store_true", default=True,
        help="No-op: este script NUNCA escribe en ninguna DB, solo genera archivos.",
    )
    args = ap.parse_args()

    ruta = Path(args.xls)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    archivos = _buscar_xls(ruta)
    if not archivos:
        print(f"ERROR: no se encontraron .xls/.xlsx en {ruta}", file=sys.stderr)
        return 2

    dfs = []
    resumenes = []
    vistos_contenido = {}
    for archivo in archivos:
        print(f"Procesando: {archivo}")
        try:
            df_items, avisos, resumen = procesar_archivo(archivo, args.hito, args.anio)
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            continue
        for a in avisos:
            print(f"  · {a}")
        if df_items is None:
            continue

        # Detección de duplicados por CONTENIDO (no solo por Hito/Año/Curso):
        # el caso confirmado (BÁSICA/2026/01-DIAGNÓSTICO vs 02-INTERMEDIO,
        # 1° básico Lectura) trae la MISMA descarga con Hito distinto según
        # la carpeta — el contenido (Logro por ítem) es idéntico porque es
        # el mismo archivo mal archivado, no una carga real de Diagnóstico.
        # Entre los dos, se conserva el que tiene el Hito de carpeta
        # consistente con la palabra clave del nombre de archivo (ej.
        # '...monitoreo...' -> INTERMEDIO) y se descarta el otro.
        clave_contenido = (
            resumen.get("anio"), resumen.get("curso"),
            tuple(resumen.get("logro_por_item", {}).items()),
        )
        if clave_contenido in vistos_contenido:
            idx_previo, archivo_previo, hito_previo = vistos_contenido[clave_contenido]
            este_limpio = hito_coincide_con_nombre(archivo, resumen.get("hito"))
            previo_limpio = hito_coincide_con_nombre(Path(archivo_previo), hito_previo)
            if este_limpio and not previo_limpio:
                # el actual es el "bueno": reemplaza al que ya estaba guardado
                print(
                    f"  AVISO: contenido IDÉNTICO a '{archivo_previo}' (Hito "
                    f"{hito_previo}, nombre inconsistente con esa carpeta) — "
                    f"se reemplaza por este archivo (Hito {resumen.get('hito')}, "
                    f"nombre consistente). El descartado queda anotado en el "
                    f"resumen; revisar manualmente antes de cargar."
                )
                resumenes[idx_previo]["duplicado_de"] = str(archivo)
                dfs[idx_previo] = df_items
                vistos_contenido[clave_contenido] = (idx_previo, str(archivo), resumen.get("hito"))
                resumen["reemplaza_a"] = archivo_previo
                resumenes.append(resumen)
            else:
                print(
                    f"  AVISO: contenido IDÉNTICO (mismos Logro por ítem, Año y "
                    f"Curso) a '{archivo_previo}' (Hito {hito_previo}) — parece "
                    f"ser la misma descarga mal archivada bajo dos hitos "
                    f"distintos. Se descarta este archivo (Hito {resumen.get('hito')}) "
                    f"para no duplicar filas en metric_data; revisar manualmente "
                    f"cuál carpeta es la correcta antes de cargar."
                )
                resumen["duplicado_de"] = archivo_previo
                resumenes.append(resumen)
            continue
        vistos_contenido[clave_contenido] = (len(dfs), str(archivo), resumen.get("hito"))

        dfs.append(df_items)
        resumenes.append(resumen)

    if not dfs:
        print("Sin resultados: ningún archivo válido de 1° básico monitoreo.", file=sys.stderr)
        return 1

    df_final = pd.concat(dfs, ignore_index=True)

    csv_cols = BASE_COLS + ["Hito", "Asignatura", "Año"]
    csv_path = out_dir / "items_1basico.csv"
    df_final[csv_cols].to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\nEscrito: {csv_path} ({len(df_final)} filas)")

    registros_metric7 = construir_metric7_json(df_final)
    json_path = out_dir / "items_1basico_metric7.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(registros_metric7, f, ensure_ascii=False, indent=2)
    print(f"Escrito: {json_path} ({len(registros_metric7)} registros)")

    resumen_path = out_dir / "items_1basico_resumen.json"
    with open(resumen_path, "w", encoding="utf-8") as f:
        json.dump(resumenes, f, ensure_ascii=False, indent=2)
    print(f"Escrito: {resumen_path}")

    print("\n--dry-run: no se escribió en ninguna base de datos (este script no tiene modo de carga real).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
