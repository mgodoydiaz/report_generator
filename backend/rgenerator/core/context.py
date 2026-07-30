from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class RunContext:
    """Contexto compartido entre steps."""

    evaluation: str = ""
    run_id: str = ""
    pipeline_id: Optional[int] = None

    # Sesión SQLAlchemy y contexto de organización (inyectados desde el router)
    db: Any = None          # sqlalchemy.orm.Session
    org_id: Optional[int] = None
    # Usuario que disparó el pipeline. None si el pipeline corre sin sesión
    # (ej. cron job). Lo usa el step SaveToMetric para auditoría.
    user_id: Optional[int] = None
    base_dir: Path = field(default_factory=lambda: Path("."))
    params: Dict[str, Any] = field(default_factory=dict)

    # Archivos de entrada por rol (ej: estudiantes, preguntas, resultados, reporte_preguntas, etc.)
    inputs: Dict[str, List[Path]] = field(default_factory=dict)

    # Artifacts intermedios (dataframes, rutas, métricas, tablas listas, etc.)
    artifacts: Dict[str, Any] = field(default_factory=dict)

    # Salidas por rol (ej: consolidado_estudiantes, consolidado_preguntas, informe_pdf, etc.)
    outputs: Dict[str, Path] = field(default_factory=dict)

    # Rutas calculadas durante InitRun
    inputs_dir: Optional[Path] = None
    outputs_dir: Optional[Path] = None
    aux_dir: Optional[Path] = None
    work_dir: Optional[Path] = None

    # Estado
    last_step: Optional[str] = None
    last_artifact_key: Optional[str] = None
    status: str = "NEW"  # NEW, RUNNING, NEEDS_REVIEW, DONE, FAILED

    # Advertencias no bloqueantes acumuladas durante la corrida (ej. una
    # dimensión de la métrica que quedó sin poblar). El runner las expone en
    # el resultado de cada paso para que el frontend pueda mostrarlas.
    warnings: List[str] = field(default_factory=list)

    def add_warning(self, message: str) -> None:
        """Registra una advertencia no bloqueante del run (idempotente)."""
        if not message:
            return
        if self.warnings is None:
            self.warnings = []
        if message not in self.warnings:
            self.warnings.append(message)

    def show_attrs(self, indent: int = 2):
        space = " " * indent
        lines = [f"{self.__class__.__name__}"]

        for attr, value in vars(self).items():
            if isinstance(value, dict):
                lines.append(f"{space}{attr}:")
                for k, v in value.items():
                    lines.append(f"{space*2}{k}: {v}")
            elif isinstance(value, list):
                lines.append(f"{space}{attr}:")
                for i, v in enumerate(value):
                    lines.append(f"{space*2}[{i}] {v}")
            else:
                lines.append(f"{space}{attr}: {value}")
        logger.debug("\n".join(lines))
