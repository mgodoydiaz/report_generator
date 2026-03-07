"""
Re-exportaciones de compatibilidad.

Este módulo re-exporta todas las clases de steps desde sus módulos especializados,
permitiendo que el código existente (pipeline_tools.py, tests, configs) siga
funcionando sin cambios.

Módulos especializados:
    - init_steps.py   : InitRun, LoadConfigFromSpec  (LoadConfig DEPRECADO)
    - io_steps.py     : DiscoverInputs, RequestUserFiles, ExportConsolidatedExcel, DeleteTempFiles
    - etl_steps.py    : RunExcelETL, EnrichWithUserInput, EnrichWithContext, ModifyColumnValues
    - report_steps.py : GenerateGraphics, GenerateTables, RenderReport, GenerateDocxReport
"""

from .init_steps import InitRun, LoadConfigFromSpec  # LoadConfig DEPRECADO
from .io_steps import DiscoverInputs, RequestUserFiles, ExportConsolidatedExcel, DeleteTempFiles
from .etl_steps import RunExcelETL, EnrichWithUserInput, EnrichWithContext, EnrichWithLookup, ModifyColumnValues
from .report_steps import GenerateGraphics, GenerateTables, RenderReport, GenerateDocxReport

__all__ = [
    # Init
    "InitRun",
    # "LoadConfig",  # DEPRECADO: usar LoadConfigFromSpec
    "LoadConfigFromSpec",
    # I/O
    "DiscoverInputs",
    "RequestUserFiles",
    "ExportConsolidatedExcel",
    "DeleteTempFiles",
    # ETL
    "RunExcelETL",
    "EnrichWithUserInput",
    "EnrichWithContext",
    "EnrichWithLookup",
    "ModifyColumnValues",
    # Report
    "GenerateGraphics",
    "GenerateTables",
    "RenderReport",
    "GenerateDocxReport",
]
