"""Runner ETL SIMCE usando archivo de parámetros .txt"""

import os
import argparse
import pandas as pd # Posiblemente haya que quitarla

from rgenerator.etl.simce_etl import (
    crear_df_resultados_estudiantes,
    crear_df_resultados_preguntas,
    guardar_dataframe_como_excel,
)

from rgenerator.tooling.config_tools import cargar_config_desde_txt, parsear_lista_desde_config


def main():
    parser = argparse.ArgumentParser(
        description="Runner ETL SIMCE usando un archivo de configuración .txt"
    )

    parser.add_argument(
        "config_file",
        type=str,
        help="Ruta al archivo .txt con la configuración de la ETL",
    )

    args = parser.parse_args()

    ruta_config = args.config_file
    if not os.path.exists(ruta_config):
        raise FileNotFoundError(f"No se encontró el archivo de configuración: {ruta_config}")

    config = cargar_config_desde_txt(ruta_config)

    tipo_etl = config.get("tipo_etl", "estudiantes").lower()
    nombre_salida = config.get("nombre_salida", "salida_etl.xlsx")

    if tipo_etl == "estudiantes":
        # Parámetros esperados en el .txt
        directorio_archivos = config["directorio_archivos"]
        mes = config["mes"]
        numero_prueba = int(config["numero_prueba"])
        asignatura = config["asignatura"]
        linea_header = int(config["linea_header"])
        columnas_relevantes = parsear_lista_desde_config(config, "columnas_relevantes")

        df_res = crear_df_resultados_estudiantes(
            directorio_archivos=directorio_archivos,
            mes=mes,
            numero_prueba=numero_prueba,
            columnas_relevantes=columnas_relevantes,
            linea_header=linea_header,
            asignatura=asignatura,
        )

        guardar_dataframe_como_excel(df_res, nombre_salida)

    elif tipo_etl == "preguntas":
        # Parámetros esperados en el .txt
        directorio_archivos = config["directorio_archivos"]
        asignatura = config["asignatura"]
        archivo_habilidades = config["archivo_habilidades"]
        columnas_relevantes_habilidades = parsear_lista_desde_config(
            config, "columnas_relevantes_habilidades"
        )

        df_res = crear_df_resultados_preguntas(
            directorio_archivos=directorio_archivos,
            asignatura=asignatura,
            archivo_habilidades=archivo_habilidades,
            columnas_relevantes_habilidades=columnas_relevantes_habilidades,
        )

        guardar_dataframe_como_excel(df_res, nombre_salida)

    else:
        raise ValueError(f"tipo_etl no reconocido en el .txt: {tipo_etl}")

    print(f"ETL '{tipo_etl}' terminada. Archivo generado: {nombre_salida}")


if __name__ == "__main__":
    main()
