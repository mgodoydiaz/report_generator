from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .context import RunContext 

@dataclass
class Step:
    """Paso base de la ETL.

    Idea:
    - Se hereda para crear pasos concretos (Load, Clean, Merge, Export, Report, DB, etc.)
    - Cada paso tiene un nombre y puede declarar qué archivos/artifacts espera y qué produce.
    - El método run ejecuta el paso.

    Nota:
    - Esta clase es intencionalmente simple para que sea fácil extenderla.
    """

    name: str
    description: str = ""

    # Qué necesita y qué produce (nombres de artifacts). Esto ayuda a validar el pipeline.
    requires: List[str] = field(default_factory=list)
    produces: List[str] = field(default_factory=list)

    # Parámetros del paso (configurable desde tu software más adelante)
    params: Dict[str, Any] = field(default_factory=dict)

    def validate(self, ctx: "RunContext") -> None:
        """Chequeos simples antes de correr el paso."""
        missing = [k for k in self.requires if k not in ctx.artifacts]
        if missing:
            raise ValueError(f"Step '{self.name}' requiere artifacts faltantes: {missing}")

    def run(self, ctx: "RunContext") -> None:
        """Ejecuta el paso.

        Se implementa en subclases.
        """
        raise NotImplementedError("Implementa run() en tu Step concreto")

    def _snapshot_artifacts(self, ctx: "RunContext") -> Dict[str, int]:
        if not hasattr(ctx, "artifacts") or ctx.artifacts is None:
            return {}
        return {k: id(v) for k, v in ctx.artifacts.items()}

    def _log_artifacts_delta(self, ctx: "RunContext", before: Dict[str, int]) -> None:
        if not hasattr(ctx, "artifacts") or ctx.artifacts is None:
            print(f"[{self.name}] Artifacts no disponibles.")
            return

        after = {k: id(v) for k, v in ctx.artifacts.items()}
        added = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        changed = sorted(k for k in set(after) & set(before) if after[k] != before[k])

        if not added and not removed and not changed:
            print(f"[{self.name}] Artifacts sin cambios.")
            return

        parts = []
        if added:
            parts.append(f"agregados={added}")
        if removed:
            parts.append(f"removidos={removed}")
        if changed:
            parts.append(f"actualizados={changed}")
        print(f"[{self.name}] Artifacts: " + "; ".join(parts))

    def show_attrs(self, indent: int = 2):
        space = " " * indent
        print(f"{self.__class__.__name__}")

        for attr, value in vars(self).items():
            if isinstance(value, dict):
                print(f"{space}{attr}:")
                for k, v in value.items():
                    print(f"{space*2}{k}: {v}")
            elif isinstance(value, list):
                print(f"{space}{attr}:")
                for i, v in enumerate(value):
                    print(f"{space*2}[{i}] {v}")
            else:
                print(f"{space}{attr}: {value}")