"""
Re-exportaciones de compatibilidad.

Este módulo re-exporta todas las clases de steps desde sus módulos especializados,
permitiendo que el código existente (pipeline_tools.py, tests, configs) siga
funcionando sin cambios.

Módulos especializados:
    - init_steps.py   : InitRun, LoadConfigFromSpec
    - io_steps.py     : RequestUserFiles
    - etl_steps.py    : RunExcelETL, EnrichWithUserInput, EnrichWithContext,
                        EnrichWithLookup, ModifyColumnValues, ApplyDerivedFields
    - pdf_steps.py    : RunDIAPDFExtraction
    - report_steps.py : RenderHtmlReport, RenderPDFReport
"""

from .init_steps import InitRun, LoadConfigFromSpec
from .io_steps import RequestUserFiles
from .etl_steps import RunExcelETL, EnrichWithUserInput, EnrichWithContext, EnrichWithLookup, ModifyColumnValues, ApplyDerivedFields
from .pdf_steps import RunDIAPDFExtraction
from .validate_steps import ValidateDataframe
from .report_steps import RenderHtmlReport, RenderPDFReport

__all__ = [
    # Init
    "InitRun",
    "LoadConfigFromSpec",
    # I/O
    "RequestUserFiles",
    # ETL
    "RunExcelETL",
    "EnrichWithUserInput",
    "EnrichWithContext",
    "EnrichWithLookup",
    "ModifyColumnValues",
    "ApplyDerivedFields",
    # PDF
    "RunDIAPDFExtraction",
    # Validate
    "ValidateDataframe",
    # Report
    "RenderHtmlReport",
    "RenderPDFReport",
]
