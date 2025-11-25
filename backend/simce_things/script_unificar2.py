from funciones import *
import os

# Se setea el directorio de trabajo a la carpeta del script
os.chdir(os.path.dirname(os.path.abspath(__file__)))

df_estudiantes = pd.read_excel("simce_2025_estudiantes.xlsx")

# Se actualiza el dataframe simce_2025_estudiantes.xlsx agregando el avance promedio, usando la funcion calcular_avance_promedio
df_estudiantes['Avance Promedio'] = 0.0
for index, row in df_estudiantes.iterrows():
    df_estudiantes.at[index, 'Avance Promedio'] = calcular_avance_promedio(df_estudiantes, row['RUT'], row['Asignatura'], row['Numero_Prueba'])

# Se guarda el dataframe actualizado
df_estudiantes.to_excel("simce_2025_estudiantes.xlsx", index=False)

# Se crean los dataframes para lenguaje y matemáticas usando la función crear_tabla
df_lenguaje = crear_tabla(df_estudiantes, 'LENGUAJE', 'todos', 4)
df_matematicas = crear_tabla(df_estudiantes, 'MATEMATICAS', 'todos', 4)

# Se guardan los dataframes en el formato asignatura_octubre_estudiantes.xlsx
df_lenguaje.to_excel("lenguaje_octubre_estudiantes.xlsx", index=False)
df_matematicas.to_excel("matematicas_octubre_estudiantes.xlsx", index=False)
print("Archivos lenguaje_octubre_estudiantes.xlsx y matematicas_octubre_estudiantes.xlsx creados con éxito.")

