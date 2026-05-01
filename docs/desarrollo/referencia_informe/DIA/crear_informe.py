"""Script para crear el informe en LaTeX"""
from funciones import *
import pandas as pd
import json
import os

# Se cargan datos de los dataframes

df_estudiantes = pd.read_excel("resultados_estudiantes_consolidado.xlsx")
df_preguntas = pd.read_excel("resultados_preguntas_consolidado.xlsx")

#df_estudiantes = pd.read_excel("res_estudiantes.xlsx")
#df_preguntas = pd.read_excel("res_preguntas.xlsx")

# Se crean gráficos y tablas en carpeta aux_files

# Se crea carpeta aux_files si no existe
if not os.path.exists("aux_files"):
    os.makedirs("aux_files")

# Resumen por curso
resumen_por_curso = resumen_por_curso(df_estudiantes)
resumen_por_curso.to_excel("aux_files/resumen_por_curso.xlsx", index=False)

# Logro promedio por nivel
logro_promedio_por_nivel(df_estudiantes)

# Logro promedio por curso
logro_promedio_por_curso(df_estudiantes)

# Distribución de rendimiento por curso
boxplot_logro_por_curso(df_estudiantes)

# Logro promedio por eje
logro_promedio_por_eje(df_preguntas)

# Logro promedio por habilidad
logro_promedio_por_habilidad(df_preguntas)

# Alumnos por nivel
alumnos_por_nivel(df_estudiantes)

try:
    # Comparación entre diagnóstico e intermedio
    df_diagnostico = pd.read_excel("info_diagnostico.xlsx")
    df_intermedio = pd.read_excel("resultados_estudiantes_consolidado.xlsx")
    df_comparacion = crear_df_comparacion(df_diagnostico, df_intermedio)
    comparacion_logro_por_curso(df_comparacion)
except:
    pass


# Se carga el esquema del informe desde el archivo esquema_informe.json a un diccionario
with open("esquema_informe.json", "r", encoding="utf-8") as f:
    esquema_informe = json.load(f)

# Se crea una lista con los cursos únicos en orden alfanumérico
cursos = df_estudiantes["Curso"].unique().tolist()
cursos.sort()
# Lista para mostrar los cursos sin el texto adicional entre paréntesis
cursos_show = [c.split(" (")[0] for c in cursos]

# Se van generando las tablas de logro por alumno y logro por pregunta para cada curso
# Al mismo tiempo se van creando las secciones y contenidos del informe y agregando al esquema_informe en la llave "secciones_dinamicas"

for curso, curso_show in zip(cursos, cursos_show):
    # Tabla logro por alumno
    df_tabla_logro_por_alumno = tabla_logro_por_alumno(df_estudiantes, curso)
    df_tabla_logro_por_alumno.to_excel(f"aux_files/tabla_logro_por_alumno_{curso_show}.xlsx", index=False)
    esquema_informe["secciones_dinamicas"].append({
        "titulo": f"Logro por Alumno - {curso_show}",
        "tipo" : "tabla",
        "contenido": f"aux_files/tabla_logro_por_alumno_{curso_show}.xlsx"
    })

    # Tabla logro por pregunta
    df_tabla_logro_por_pregunta = tabla_logro_por_pregunta(df_preguntas, curso)
    df_tabla_logro_por_pregunta.to_excel(f"aux_files/tabla_logro_por_pregunta_{curso_show}.xlsx", index=False)
    esquema_informe["secciones_dinamicas"].append({
        "titulo": f"Logro por Pregunta - {curso_show}",
        "tipo" : "tabla",
        "contenido": f"aux_files/tabla_logro_por_pregunta_{curso_show}.xlsx"
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
os.remove("informe.aux")
os.remove("informe.log")
# Se mueve el informe y las variables a la carpeta aux_files
os.replace("informe.tex", "aux_files/informe.pdf")
os.replace("variables.tex", "aux_files/variables.tex")

# Se elimina la carpeta con _pycache
import shutil
shutil.rmtree("__pycache__", ignore_errors=True)
#
