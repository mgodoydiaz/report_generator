from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class RunContext:
    """Contexto compartido entre steps.
    
    Parameters:
    ---------------
    evaluation: str
        Nombre de la evaluación (ej: 'simce', 'psu', etc.)
    
    run_id: str
        Identificador único de la corrida (ej: timestamp, UUID, etc.)

    base_dir: Path
        Directorio base donde se encuentran inputs, outputs, etc.

    params: Dict[str, Any]
        Parámetros generales de la corrida (configuración, opciones, etc.) 
        """

    evaluation: str
    run_id: str
    base_dir: Path
    params: Dict[str, Any] = field(default_factory=dict)

    # Archivos de entrada por rol (ej: estudiantes, preguntas, resultados, reporte_preguntas, etc.)
    inputs: Dict[str, List[Path]] = field(default_factory=dict)

    # Artifacts intermedios (dataframes, rutas, métricas, tablas listas, etc.)
    artifacts: Dict[str, Any] = field(default_factory=dict)

    # Salidas por rol (ej: consolidado_estudiantes, consolidado_preguntas, informe_pdf, etc.)
    outputs: Dict[str, Path] = field(default_factory=dict)

    # Estado
    last_step: Optional[str] = None
    status: str = "NEW"  # NEW, RUNNING, NEEDS_REVIEW, DONE, FAILED
