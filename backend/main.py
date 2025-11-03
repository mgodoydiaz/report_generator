#!/usr/bin/env python3
"""
main.py
Punto de entrada del backend de report_generator.

Ejemplos de uso:
    python main.py etl data/
    python main.py report esquema_informe.json
"""

import argparse
import logging
import os

# Importar módulos propios
from etl import (
    reconocer_cursos,
    extraer_establecimiento_y_curso,
    reemplazar_nivel_logro,
    calcular_nivel_logro,
    obtener_nivel,
)
from reports import informe

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("report_generator")


def run_etl(data_dir: str):
    """
    Ejecuta el proceso ETL sobre la carpeta indicada.
    Por ahora, solo lista los archivos XLS y PDF encontrados.
    """
    logger.info("Iniciando ETL en carpeta: %s", data_dir)
    archivos = os.listdir(data_dir)
    archivos_xls = [a for a in archivos if a.endswith(".xls")]
    archivos_pdf = [a for a in archivos if a.endswith(".pdf")]

    logger.info("Archivos XLS encontrados: %d", len(archivos_xls))
    logger.info("Archivos PDF encontrados: %d", len(archivos_pdf))
    # Aquí puedes llamar funciones más completas del módulo etl
    # ejemplo: consolidar_dia.procesar(archivos_xls, archivos_pdf)


def run_report(esquema_path: str):
    """
    Genera informe en PDF a partir de un esquema JSON.
    """
    logger.info("Generando informe desde esquema: %s", esquema_path)
    informe.crear_informe(esquema_path)  # función que moveremos a reports/informe.py


def main():
    parser = argparse.ArgumentParser(
        description="Backend de generación de reportes académicos"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcomando ETL
    parser_etl = subparsers.add_parser("etl", help="Ejecutar proceso ETL")
    parser_etl.add_argument("data_dir", help="Carpeta con archivos XLS y PDF")

    # Subcomando Reporte
    parser_report = subparsers.add_parser("report", help="Generar informe PDF")
    parser_report.add_argument(
        "esquema_path", help="Ruta al archivo esquema_informe.json"
    )

    args = parser.parse_args()

    if args.command == "etl":
        run_etl(args.data_dir)
    elif args.command == "report":
        run_report(args.esquema_path)


if __name__ == "__main__":
    main()
