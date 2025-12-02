"""Funciones y acciones ETL para datos SIMCE"""

import os
import pandas as pd

# Se agrega a sys el path de la libreria rgenerator
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from rgenerator.tooling.etl_tools import agregar_columnas_dataframe, limpiar_columnas


BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
INPUT_DIR = os.path.join(BASE_DIR, 'data', 'input')
OUTPUT_DIR = os.path.join(BASE_DIR, 'data', 'output')
TEMP_DIR = os.path.join(BASE_DIR, 'data', 'temp')

# Funcion para consolidar los resultados por estudiante de una carpeta

def crear_df_resultados_estudiantes(
        directorio_archivos: str,
        mes: str,
        numero_prueba: int,
        asignatura: str,
        linea_header: int,
        columnas_relevantes: list = ["Nombre", "RUT", "Curso", "B","M","O", "Puntaje", "Rend", "SIMCE", "Nota", "Logro"]
):
    df_list = []
    dir_archivos = os.path.join(INPUT_DIR, directorio_archivos)
    lista_archivos = os.listdir(dir_archivos)
    for archivo in lista_archivos:
        ruta_archivo = os.path.join(dir_archivos, archivo)
        if archivo.endswith(".xlsx") and not "ReportePregunta" in archivo and not "simce_2025" in archivo and not "habilidades" in archivo:
            datos = (asignatura, mes, numero_prueba)
            temp_df = pd.read_excel(ruta_archivo, header=linea_header)
            temp_df = temp_df[columnas_relevantes]
            temp_df = agregar_columnas_dataframe(temp_df, datos)
            temp_df = limpiar_columnas(temp_df)
            df_list.append(temp_df)
    df_consolidado = pd.concat(df_list, ignore_index=True)
    return df_consolidado

def crear_mapa_habilidades(
        ruta_archivo: str,
        columnas_relevantes: list,
):
    df = pd.read_excel(ruta_archivo)
    df = df[columnas_relevantes]
    # Se crea un diccionario donde la clave es el primer elemento  de la lista columnas_relevantes, y el valor una tupla con el resto de los elementos
    mapa_habilidades = {}
    for index, row in df.iterrows():
        clave = row[columnas_relevantes[0]]
        valores = tuple(row[col] for col in columnas_relevantes[1:])
        mapa_habilidades[clave] = valores
    return mapa_habilidades

def crear_df_resultados_preguntas(
        directorio_archivos: str,
        asignatura: str,
        archivo_habilidades: str,
        columnas_relevantes_habilidades: list,

):
    df_list = []
    dir_archivos = os.path.join(INPUT_DIR, directorio_archivos)
    lista_archivos = os.listdir(dir_archivos)
    lista_archivos = [f for f in lista_archivos if "ReportePregunta" in f]
    mapa_habilidades = crear_mapa_habilidades(
        ruta_archivo=os.path.join(INPUT_DIR, archivo_habilidades),
        asignatura=asignatura,
        columnas_relevantes=columnas_relevantes_habilidades
    )
    for archivo in lista_archivos:
        ruta_archivo = os.path.join(dir_archivos, archivo)
        temp_df = transformar_archivo_excel_a_dataframe(ruta_archivo, header=55)
        temp_df["Asignatura"] = asignatura
        # Se agrega la columna de habilidades usando el mapa_habilidades
        temp_df[columnas_relevantes_habilidades[1:]] = temp_df['Pregunta'].map(mapa_habilidades)
        df_list.append(temp_df)

    df_consolidado = pd.concat(df_list, ignore_index=True)
    return df_consolidado

def transformar_archivo_excel_a_dataframe(ruta_archivo, header):
    df = pd.read_excel(ruta_archivo, header=header)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    df.columns = df.columns.str.replace('Cant..4', 'E', n=1)
    df.columns = df.columns.str.replace('Cant..3', 'D', n=1)
    df.columns = df.columns.str.replace('Cant..2', 'C', n=1)
    df.columns = df.columns.str.replace('Cant..1', 'B', n=1)
    df.columns = df.columns.str.replace('Cant.', 'A', n=1)
    df = df.drop(columns=[col for col in df.columns if '%' in col])
    df = df.drop(columns=['P. Correcta'])
    df = df.rename(columns={'Distractor\n': 'Distractor'})
    df['Curso'] = '2' + ruta_archivo.split('.xlsx')[0][-1]
    return df

def guardar_dataframe_como_excel(df: pd.DataFrame, nombre_archivo: str, crear_nuevo: bool = False, ruta_salida: str = OUTPUT_DIR) -> None:
    if not os.path.exists(ruta_salida):
        os.makedirs(ruta_salida)
        
    archivo_salida = os.path.join(ruta_salida, nombre_archivo)
    if crear_nuevo and os.path.exists(archivo_salida):
        os.remove(archivo_salida)
    if not crear_nuevo and os.path.exists(archivo_salida):
        df_existente = pd.read_excel(archivo_salida)
        df_combinado = pd.concat([df_existente, df], ignore_index=True)
        df_combinado.to_excel(archivo_salida, index=False)
    else:
        df.to_excel(archivo_salida, index=False)
    return None