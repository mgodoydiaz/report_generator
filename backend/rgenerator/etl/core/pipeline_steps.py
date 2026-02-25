"""
Re-exportaciones de compatibilidad.

Este módulo re-exporta todas las clases de steps desde sus módulos especializados,
permitiendo que el código existente (pipeline_tools.py, tests, configs) siga
funcionando sin cambios.

Módulos especializados:
    - init_steps.py   : InitRun, LoadConfig, LoadConfigFromSpec
    - io_steps.py     : DiscoverInputs, RequestUserFiles, ExportConsolidatedExcel, DeleteTempFiles
    - etl_steps.py    : RunExcelETL, EnrichWithUserInput, EnrichWithContext, ModifyColumnValues
    - report_steps.py : GenerateGraphics, GenerateTables, RenderReport, GenerateDocxReport
"""

from .init_steps import InitRun, LoadConfig, LoadConfigFromSpec
from .io_steps import DiscoverInputs, RequestUserFiles, ExportConsolidatedExcel, DeleteTempFiles
from .etl_steps import RunExcelETL, EnrichWithUserInput, EnrichWithContext, ModifyColumnValues
from .report_steps import GenerateGraphics, GenerateTables, RenderReport, GenerateDocxReport

__all__ = [
    # Init
    "InitRun",
    "LoadConfig",
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
    "ModifyColumnValues",
    # Report
    "GenerateGraphics",
    "GenerateTables",
    "RenderReport",
    "GenerateDocxReport",
]
