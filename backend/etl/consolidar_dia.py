"""
consolidar_dia.py
Módulo ETL para consolidar resultados DIA desde archivos XLS y PDF.
"""

import os
import re
import pandas as pd
import numpy as np
import xlrd
import camelot
import fitz  # PyMuPDF
from PIL import Image
from tqdm import tqdm

from . import (
    reconocer_cursos,
    region_darkness,
    extract_bold_alternatives,
    get_correct_percent,
    reemplazar_nivel_logro,
    calcular_nivel_logro,
    obtener_nivel,
    extraer_establecimiento_y_curso,
)


def procesar_xls(archivos_xls):
    """
    Procesa los archivos XLS y devuelve un DataFrame consolidado de estudiantes.
    """
    resultados_estudiantes = pd.DataFrame()

    for xls_file in tqdm(archivos_xls, desc="Procesando archivos XLS"):
        workbook = xlrd.open_workbook(xls_file)
        sheet = workbook.sheet_by_index(0)

        establecimiento = sheet.cell_value(4, 1)
        curso = sheet.cell_value(5, 1)

        df = pd.read_excel(xls_file, header=12)

        # Se guarda el establecimiento y curso en el dataframe
        df['Establecimiento'] = establecimiento
        df['Curso'] = curso

        resultados_estudiantes = pd.concat([resultados_estudiantes, df], ignore_index=True)

    # Limpieza y columnas adicionales
    resultados_estudiantes.iloc[:, 2:-3] = resultados_estudiantes.iloc[:, 2:-3].replace(',', '.', regex=True)
    resultados_estudiantes.iloc[:, 2:-3] = resultados_estudiantes.iloc[:, 2:-3].astype(float)

    resultados_estudiantes['Logro'] = resultados_estudiantes.iloc[:, 2:-3].mean(axis=1) / 100
    resultados_estudiantes['NIVEL DE LOGRO'] = reemplazar_nivel_logro(resultados_estudiantes['NIVEL DE LOGRO'])
    resultados_estudiantes['Nivel'] = resultados_estudiantes['Curso'].apply(obtener_nivel)

    return resultados_estudiantes


def procesar_pdf(archivos_pdf, indice_curso=3, dic_pages_por_curso=None):
    """
    Procesa los archivos PDF y devuelve un DataFrame consolidado de preguntas.
    """
    resultados_preguntas = pd.DataFrame()

    for archivo_pdf in tqdm(archivos_pdf, desc="Procesando archivos PDF"):
        partes = archivo_pdf.split('_')
        curso = partes[indice_curso]
        pages = dic_pages_por_curso.get(curso)

        tablas = camelot.read_pdf(archivo_pdf, pages=pages, flavor="lattice")
        tablas_impares = [t for i, t in enumerate(tablas) if i % 2 == 1]

        establecimiento, curso, _ = extraer_establecimiento_y_curso(archivo_pdf)

        df_intermedio = pd.concat([t.df.iloc[1:] for t in tablas_impares], ignore_index=True)

        # Rango de páginas para respuestas correctas
        page_start, page_end = map(int, pages.split('-'))
        page_start -= 1
        page_end += 1

        respuestas_correctas = extract_bold_alternatives(archivo_pdf, start_page=page_start, end_page=page_end, x_min=450)

        i = 0
        j = 0
        for row in df_intermedio.itertuples(index=False):
            if "RC" in row[5]:
                valores = row[5].split('RC:')
                rc = valores[1].split('\n')[0].strip()
                rc = float(rc.replace('%', ''))/100
                df_intermedio.at[j, 7] = rc
            else:
                r_correcta = respuestas_correctas[i]['winner']
                porcentaje = get_correct_percent(row[5], r_correcta)
                porcentaje = float(porcentaje)/100
                df_intermedio.at[j, 7] = porcentaje
                i += 1
            j += 1

        df_intermedio.at[:,8] = establecimiento
        df_intermedio.at[:,9] = curso

        resultados_preguntas = pd.concat([resultados_preguntas, df_intermedio], ignore_index=True)

    resultados_preguntas.columns = [
        "N° Pregunta", "N° OA", "Eje Temático", "Habilidad", 
        "Indicador de evaluación", "% respuestas", "Logro", 
        "Establecimiento", "Curso"
    ]

    # Limpieza
    for col in ["Eje Temático", "Habilidad", "Indicador de evaluación", "% respuestas"]:
        resultados_preguntas[col] = resultados_preguntas[col].str.replace('\n', '')

    resultados_preguntas['Nivel de Logro'] = resultados_preguntas['Logro'].apply(calcular_nivel_logro)
    resultados_preguntas['Nivel'] = resultados_preguntas['Curso'].apply(obtener_nivel)

    return resultados_preguntas


def consolidar(data_dir, indice_curso=3, dic_pages_por_curso=None,
               out_estudiantes="resultados_estudiantes_consolidado.xlsx",
               out_preguntas="resultados_preguntas_consolidado.xlsx"):
    """
    Función principal: procesa XLS y PDF de un directorio y guarda resultados en Excel.
    """
    archivos = os.listdir(data_dir)
    archivos_xls = [os.path.join(data_dir, a) for a in archivos if a.endswith(".xls")]
    archivos_pdf = [os.path.join(data_dir, a) for a in archivos if a.endswith(".pdf")]

    df_estudiantes = procesar_xls(archivos_xls)
    df_estudiantes.to_excel(out_estudiantes, index=False)

    df_preguntas = procesar_pdf(archivos_pdf, indice_curso=indice_curso, dic_pages_por_curso=dic_pages_por_curso or {})
    df_preguntas.to_excel(out_preguntas, index=False)

    return df_estudiantes, df_preguntas
