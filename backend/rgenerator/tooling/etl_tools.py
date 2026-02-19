import pandas as pd
import numpy as np
import re


def agregar_columnas_dataframe(df, datos):
    """Agrega columnas de asignatura, mes y numero de prueba a un DataFrame dado."""
    asignatura, mes, numero_prueba = datos
    df["Asignatura"] = asignatura
    df["Mes"] = mes
    df["Numero_Prueba"] = numero_prueba
    return df


def limpiar_columnas(df):
    """Teniendo las columnas Rend y Curso se modifian tal que:
    1) Rend quede como un número entre 0 y 1. A veces está en porcentaje o en número de 0 a 100.
    2) Curso se elimine la parte de '° medio ' y quede solo el número y la letra sin espacios.
    3) Si los  nombres de columnas tienen B, M, O se reemplazan por Buenas, Malas, Omitidas respectivamente.
    """
    # Renombrar columnas B, M, O
    df = df.rename(columns={"B": "Buenas", "M": "Malas", "O": "Omitidas"})
    # Se elimina columna de Avance si existe
    if "Avance" in df.columns:
        df = df.drop(columns=["Avance"])
    # Se renombra la columna de Rut a RUT
    if "RUT" not in df.columns and "Rut" in df.columns:
        df = df.rename(columns={"Rut": "RUT"})
    # Se elimina la columna Logro II si existe
    if "Logro II" in df.columns:
        df = df.drop(columns=["Logro II"])

    # Limpiar columna Rend
    def limpiar_rend(valor):
        if isinstance(valor, str) and valor.endswith("%"):
            return float(valor.strip("%")) / 100
        elif isinstance(valor, (int, float)) and valor > 1:
            return valor / 100
        elif isinstance(valor, (int, float)):
            return valor
        else:
            return None

    if "Rend" in df.columns:
        df["Rend"] = df["Rend"].apply(limpiar_rend)

    # Limpiar columna Curso
    def limpiar_curso(curso):
        if isinstance(curso, str):
            curso = curso.replace("° medio ", "").strip()
            return curso
        return curso

    if "Curso" in df.columns:
        df["Curso"] = df["Curso"].apply(limpiar_curso)

    return df


def calcular_avance_promedio(df_estudiantes, estudiante, asignatura, numero_prueba=4):
    df_estudiante = df_estudiantes[
        (df_estudiantes["RUT"] == estudiante)
        & (df_estudiantes["Asignatura"] == asignatura)
        & (df_estudiantes["Numero_Prueba"] <= numero_prueba)
    ]
    # Se guarda en dos listas el numero de prueba y el logro obtenido
    n_pruebas, rends = [], []
    for _, row in df_estudiante.iterrows():
        n_pruebas.append(row["Numero_Prueba"])
        rends.append(row["Rend"])
    # Se calcula una regresion lineal entre n_pruebas (X) y logros (Y)
    if len(n_pruebas) > 1:
        coef = np.polyfit(n_pruebas, rends, 1)
        pendiente = coef[0]
        return pendiente
    return 0


def crear_tabla(df_estudiantes, parametros):
    asignatura = parametros["Asignatura"]
    curso = parametros.get("Curso", "todos")
    numero_prueba = parametros.get("Numero_Prueba", 4)

    df_filtrado = df_estudiantes[
        (df_estudiantes["Numero_Prueba"] <= numero_prueba)
        & (df_estudiantes["Asignatura"] == asignatura)
    ].copy()
    # Si curso dice 'todos', no se filtra por curso
    if curso != "todos":
        df_filtrado = df_filtrado[df_filtrado["Curso"] == curso].copy()
    df_filtrado["Avance_Promedio"] = 0.0
    # Se agrega la columna Avance_Promedio que se calcula con la funcion anterior
    for _, row in df_filtrado.iterrows():
        df_filtrado.at[row.name, "Avance_Promedio"] = calcular_avance_promedio(
            df_estudiantes, row["RUT"], row["Asignatura"], numero_prueba
        )
    return df_filtrado


def modificar_valores_columna(df, config_transformaciones):
    """
    Modifica valores de columnas basado en una lista de configuraciones.
    
    Args:
        df (pd.DataFrame): DataFrame a modificar
        config_transformaciones (list): Lista de diccionarios con reglas de transformación.
            Ejemplo de regla:
            {
                "columna": "Curso",
                "operacion": "regex" | "replace" | "map" | "strip",
                "parametros": { ... }
            }
            
    Returns:
        pd.DataFrame: DataFrame modificado
    """
    if not config_transformaciones:
        return df
        
    for regla in config_transformaciones:
        col = regla.get("columna")
        operacion = regla.get("operacion")
        params = regla.get("parametros", {})
        
        if col not in df.columns:
            continue
            
        if operacion == "regex":
            patron = params.get("patron")
            reemplazo = params.get("reemplazo", "")
            if patron:
                df[col] = df[col].astype(str).str.replace(patron, reemplazo, regex=True)
                
        elif operacion == "replace":
            valor_original = params.get("valor_original")
            valor_nuevo = params.get("valor_nuevo")
            df[col] = df[col].replace(valor_original, valor_nuevo)
            
        elif operacion == "map":
            mapa = params.get("mapa", {})
            default = params.get("default", None)
            if default is not None:
                df[col] = df[col].map(mapa).fillna(default)
            else:
                # Si no hay default, mantiene valores originales si no estan en el mapa
                df[col] = df[col].map(mapa).fillna(df[col])
                
        elif operacion == "strip":
            if pd.api.types.is_string_dtype(df[col]):
                 df[col] = df[col].str.strip()

    return df
