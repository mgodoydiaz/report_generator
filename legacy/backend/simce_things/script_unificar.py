"""Se unifican los archivos de datos de los diferentes años en un solo archivo CSV."""

import os
import pandas as pd

# A cada archivo se le agregan las columnas correspondientes
from funciones import calcular_avance_promedio, extraer_datos, agregar_columnas_dataframe, limpiar_columnas, crear_tabla

# Se va a buscar los archivos a la carpeta inputs de ../Lenguaje/ y ../Matematicas/
mes = "NOVIEMBRE"
numero_prueba = 5

columns_name = ["Nombre", "RUT", "Curso", "B","M","O", "Puntaje", "Rend", "SIMCE", "Nota", "Logro"]

# Carga de archivos de valores por estudiantes

# Primero con Lenguaje
df_list = []
os.chdir("../Lenguaje/inputs/")
archivos = os.listdir()
for archivo in archivos:
    print(archivo)
    if archivo.endswith(".xlsx") and not "ReportePregunta" in archivo and not "simce_2025" in archivo and not "habilidades" in archivo:
        datos = "LENGUAJE", mes, numero_prueba
        print(archivo)
        temp_df = pd.read_excel(archivo, header=23)
        temp_df = temp_df[columns_name]
        temp_df = agregar_columnas_dataframe(temp_df, datos)
        temp_df = limpiar_columnas(temp_df)
        df_list.append(temp_df)

df_lenguaje = pd.concat(df_list, ignore_index=True)

# Luego con Matemáticas
df_list = []
os.chdir("../../Matemáticas/inputs/")
archivos = os.listdir()
for archivo in archivos:
    if archivo.endswith(".xlsx") and not "ReportePregunta" in archivo and not "simce_2025" in archivo and not "habilidades" in archivo:
        datos = "MATEMATICAS", mes, numero_prueba
        temp_df = pd.read_excel(archivo, header=23)
        temp_df = temp_df[columns_name]
        temp_df = agregar_columnas_dataframe(temp_df, datos)
        temp_df = limpiar_columnas(temp_df)
        df_list.append(temp_df)
df_matematicas = pd.concat(df_list, ignore_index=True)

df_list = []

# Se vuelve a la carpeta script
os.chdir("../../Compilado/")

# Se carga el compilado de estudiantes
df_compiled_in = pd.read_excel("simce_2025_estudiantes_in.xlsx")

# Se guardan los dataframes en una lista
df_list.append(df_lenguaje)
df_list.append(df_matematicas)
df_list.append(df_compiled_in)

df_compiled = pd.concat(df_list, ignore_index=True)

# Se agrega el avance promedio para cada estudiante

# Se actualiza el dataframe simce_2025_estudiantes.xlsx agregando el avance promedio, usando la funcion calcular_avance_promedio
df_compiled['Avance Promedio'] = 0.0
for index, row in df_compiled.iterrows():
    df_compiled.at[index, 'Avance Promedio'] = calcular_avance_promedio(df_compiled, row['RUT'], row['Asignatura'], row['Numero_Prueba'])

# Se guarda el dataframe compilado en un archivo Excel
output_file = "simce_2025_estudiantes.xlsx"
df_compiled.to_excel(output_file, index=False)
print(f"Archivo {output_file} creado con éxito.")

df_lenguaje = crear_tabla(df_compiled, 'LENGUAJE', 'todos', 5)
df_matematicas = crear_tabla(df_compiled, 'MATEMATICAS', 'todos', 5)

# Se guardan los dataframes en el formato asignatura_octubre_estudiantes.xlsx
df_lenguaje.to_excel("lenguaje_octubre2_estudiantes.xlsx", index=False)
df_matematicas.to_excel("matematicas_octubre2_estudiantes.xlsx", index=False)
print("Archivos lenguaje_octubre2_estudiantes.xlsx y matematicas_octubre2_estudiantes.xlsx creados con éxito.")

