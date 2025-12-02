"""Script para crear el informe en LaTeX"""
from rgenerator import BASE_DIR,INPUT_DIR,TMP_DIR
from funciones_informe import *
import pandas as pd
import json
import os
import shutil 
import sys
sys.path.append(BASE_DIR)
parametros = {
    'Asignatura': 'LENGUAJE',
    'Numero_Prueba': 5
}

# Se cargan datos de los dataframes

ruta_archivo_estudiantes = os.path.join(INPUT_DIR, "simce_2025_estudiantes.xlsx")
ruta_archivo_preguntas = os.path.join(INPUT_DIR, "simce_2025_preguntas.xlsx")

df_estudiantes = pd.read_excel(ruta_archivo_estudiantes)
df_preguntas = pd.read_excel(ruta_archivo_preguntas)

# Se filtra por asignatura
df_estudiantes = df_estudiantes[df_estudiantes['Asignatura'] == parametros['Asignatura']].copy()
df_preguntas = df_preguntas[df_preguntas['Asignatura'] == parametros['Asignatura']].copy()

# Se filtra por numero de prueba
df_estudiantes_prueba = df_estudiantes[df_estudiantes['Numero_Prueba'] == parametros['Numero_Prueba']].copy()
#df_preguntas_prueba = df_preguntas[df_preguntas['Numero_Prueba'] == parametros['Numero_Prueba']].copy()

# Se crean gráficos y tablas en carpeta aux_files

os.chdir(TMP_DIR)

# Se crea carpeta aux_files si no existe
if not os.path.exists("aux_files"):
    os.makedirs("aux_files")

# Se copian archivos estaticos necesarios para el informe a la carpeta aux_files
# Carpeta de imagenes origen

imagenes_origen = os.path.join(BASE_DIR, "data","static", "img")
imagenes_destino = os.path.join(TMP_DIR, "img")
if not os.path.exists(imagenes_destino):
    os.makedirs(imagenes_destino)
for archivo in os.listdir(imagenes_origen):
    ruta_origen = os.path.join(imagenes_origen, archivo)
    ruta_destino = os.path.join(imagenes_destino, archivo)
    if os.path.isfile(ruta_origen):
        shutil.copy(ruta_origen, ruta_destino)


# Resumen por curso de Rendimiento y SIMCE
resumen_por_curso = resumen_estadistico_basico(df_estudiantes_prueba, 'Rend', formato="percent", agrupar_por="Curso")
resumen_por_curso.to_excel("aux_files/resumen_logro_por_curso.xlsx", index=False)

resumen_por_curso_simce = resumen_estadistico_basico(df_estudiantes_prueba, 'SIMCE', formato="number", agrupar_por="Curso")
resumen_por_curso_simce.to_excel("aux_files/resumen_simce_por_curso.xlsx", index=False)

# Rendimiento por curso en gráfico de barras
grafico_barras_promedio_por(df_estudiantes_prueba, "Rend", agrupar_por="Curso", titulo="Rendimiento Promedio por Curso", ylabel="Rendimiento (%)", nombre_grafico="aux_files/rendimiento_promedio_por_curso.png")

# Distribucion SIMCE por curso
boxplot_valor_por_curso(df_estudiantes_prueba, "SIMCE", agrupar_por="Curso", titulo_grafico="Distribución de Puntaje SIMCE por Curso", ylabel="Puntaje SIMCE", formato = "number", nombre_grafico="aux_files/distribucion_puntaje_simce_por_curso.png")

# Evolucion de Logro promedio por curso y mes
valor_promedio_agrupado_por(
    df_estudiantes,
    columna_valor="Rend",
    agrupar_principal_por="Curso",
    agrupar_secundario_por="Mes",
    titulo_grafico="Evolución del Logro Promedio por Curso y Mes",
    titulo_leyenda="Mes",
    y_lims=(0,1),
    formato="percent",
    nombre_grafico="aux_files/evolucion_logro_promedio_por_curso_y_mes.png"
)

# Evolucion de SIMCE promedio por curso y mes
valor_promedio_agrupado_por(
    df_estudiantes,
    columna_valor="SIMCE",
    agrupar_principal_por="Curso",
    agrupar_secundario_por="Mes",
    titulo_grafico="Evolución del SIMCE Promedio por Curso y Mes",
    titulo_leyenda="Mes",
    formato="number",
    nombre_grafico="aux_files/evolucion_simce_promedio_por_curso_y_mes.png"
)

# Cantidad de alumnos por nivel de logro y curso
alumnos_por_nivel_cualitativo(df_estudiantes_prueba, columna_nivel="Logro", agrupar_por="Curso", titulo_grafico="Cantidad de Alumnos por Nivel de Logro y Curso", titulo_leyenda="Nivel de Logro", ylabel="Cantidad de Alumnos", nombre_grafico="aux_files/alumnos_por_nivel.png")

# Evolucion de cantidad de alumnos por nivel de logro y curso
alumnos_por_nivel_curso_y_mes(
    df_estudiantes,
    columna_nivel="Logro",
    titulo_grafico="", # Sin titulo porque se agrega en informe
    titulo_leyenda="Nivel de Logro",
    ylabel="Cantidad de Alumnos",
    nombre_grafico="aux_files/evolucion_alumnos_por_nivel.png"
)

# Logro promedio por habilidad
valor_promedio_agrupado_por(df_preguntas, columna_valor="Logro", agrupar_principal_por="Curso", agrupar_secundario_por="Habilidad", titulo_grafico="Logro Promedio por Habilidad", titulo_leyenda="Habilidad", formato='percent', nombre_grafico="aux_files/logro_promedio_por_habilidad.png")

# Logro promedio por eje
valor_promedio_agrupado_por(df_preguntas, columna_valor="Logro", agrupar_principal_por="Curso", agrupar_secundario_por="Eje temático", titulo_grafico="Logro Promedio por Eje Temático", titulo_leyenda="Eje Temático", formato='percent', nombre_grafico="aux_files/logro_promedio_por_eje.png")

# Se carga el esquema del informe desde el archivo esquema_informe.json a un diccionario

schema_file = os.path.join(BASE_DIR, "backend","schemas", "esquema_informe_lenguaje.json")


with open(schema_file, "r", encoding="utf-8") as f:
    esquema_informe = json.load(f)

# Se crea una lista con los cursos únicos en orden alfanumérico
cursos = df_estudiantes["Curso"].unique().tolist()
cursos.sort()

# Tomando el df_preguntas, se crea una tabla de la estadistica por pregunta del establecimiento en general (se ignora el curso, se agrupa por pregunta)
estadistica_por_pregunta = crear_tabla_estadistica_por_pregunta(df_preguntas, parametros)
estadistica_por_pregunta.to_excel("aux_files/reporte_preguntas.xlsx", index=False)


# Se van generando las tablas de logro por alumno y logro por pregunta para cada curso
# Al mismo tiempo se van creando las secciones y contenidos del informe y agregando al esquema_informe en la llave "secciones_dinamicas"


for curso in cursos:
    # Tabla logro por alumno
    parametros['Curso'] = curso
    df_curso = crear_tabla(df_estudiantes, parametros)
    df_tabla_logro_por_alumno = tabla_logro_por_alumno(df_curso, parametros=parametros)
    df_tabla_logro_por_alumno.to_excel(f"aux_files/tabla_logro_por_alumno_{curso}.xlsx", index=False)
    esquema_informe["secciones_dinamicas"].append({
        "titulo": f"Logro por Alumno - {curso}",
        "tipo" : "tabla",
        "contenido": f"aux_files/tabla_logro_por_alumno_{curso}.xlsx"
    })

    # Tabla logro por pregunta
    df_tabla_logro_por_pregunta = tabla_logro_por_pregunta(df_preguntas, curso, agrupar_por="Curso")
    df_tabla_logro_por_pregunta.to_excel(f"aux_files/tabla_logro_por_pregunta_{curso}.xlsx", index=False)
    esquema_informe["secciones_dinamicas"].append({
        "titulo": f"Logro por Pregunta - {curso}",
        "tipo" : "tabla",
        "contenido": f"aux_files/tabla_logro_por_pregunta_{curso}.xlsx"
    })

# Se agrega un contador alfabetico 
i = 0
lista_indices = []

new_command_format = "\\newcommand{{\\{}}}{{{}}}\n"

# Se crea el archivo variables.tex con las variables del informe
with open("variables.tex", "w", encoding="utf-8") as f:
    
    f.write("% Variables del informe\n")
    for key, value in esquema_informe["variables_documento"].items():
        f.write(new_command_format.format(key, value))
    f.write("\n")


    f.write("% Secciones estáticas del informe\n")
    for seccion in esquema_informe["secciones_fijas"]:
        lista_indices.append(indice_alfabetico[i])
        f.write(new_command_format.format("section" + indice_alfabetico[i], "\\section*{" + seccion['titulo'] + "}"))

        if seccion["tipo"] == "tabla":
            df = pd.read_excel(seccion["contenido"])
            latex = df_a_latex_loop(df)
            f.write(new_command_format.format("content" + indice_alfabetico[i], latex))

        elif seccion["tipo"] == "imagen":
            if "options" in seccion:
                latex = img_to_latex(seccion["contenido"], seccion["options"])
            else:
                latex = img_to_latex(seccion["contenido"])
            f.write(new_command_format.format("content" + indice_alfabetico[i], latex))

        i += 1
    f.write("\n")


    f.write("% Secciones dinámicas del informe\n")
    for seccion in esquema_informe["secciones_dinamicas"]:
        lista_indices.append(indice_alfabetico[i])
        f.write(new_command_format.format("section" + indice_alfabetico[i], "\\newpage\\section*{" + seccion['titulo'] + "}"))
        if seccion["tipo"] == "tabla":
            df = pd.read_excel(seccion["contenido"])
            latex = df_a_latex_loop(df)
            f.write(new_command_format.format("content" + indice_alfabetico[i], latex))
        elif seccion["tipo"] == "imagen":
            if "options" in seccion:
                latex = img_to_latex(seccion["contenido"], seccion["options"])
            else:
                latex = img_to_latex(seccion["contenido"])
            f.write(new_command_format.format("content" + indice_alfabetico[i], latex))
        i += 1
    f.write("\n")

# Se crea el informe en LaTeX
with open ("informe.tex", "w", encoding="utf-8") as f:
    esquema_informe_latex = formato_informe_generico
    f.write(esquema_informe_latex)
    f.write("\n")
    for indice in lista_indices:
        f.write(f"\\section{indice}\n")
        f.write(f"\\content{indice}\n")
        f.write("\n")
    f.write("\n")
    f.write("\\end{document}")

# Se compila el informe en PDF
os.system("xelatex informe.tex")

# Se elimina archivos auxiliares generados por LaTeX
#os.remove("informe.aux")
#os.remove("informe.log")

# Se mueve el informe y las variables a la carpeta aux_files
os.replace("informe.tex", "aux_files/informe.tex")
os.replace("variables.tex", "aux_files/variables.tex")

# Se elimina la carpeta con _pycache
import shutil
shutil.rmtree("__pycache__", ignore_errors=True)
#
