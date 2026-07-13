"""Generador de informes Word por indicador — registro por nombre.

Cada informe es UN archivo Python en `informes/<nombre>.py` + UNA plantilla
Word en `templates/<nombre>.docx`. El nombre del archivo ES el identificador
público: el frontend llama `POST /api/reports/word/<nombre>` y el registry
resuelve directamente al módulo.

Crear un informe nuevo:
    python scripts/nuevo_informe_word.py mi_informe --label "Mi Informe"

API pública:
    get_registry()            → dict {nombre: módulo} (auto-descubierto)
    obtener_modulo(nombre)    → módulo o KeyError
    listar_informes()         → metadata para el frontend
"""
from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType

from . import engine  # noqa: F401 — re-export
from .engine import render_informe, listar_placeholders, resolver_plantilla  # noqa: F401

_registry: dict[str, ModuleType] | None = None


def get_registry(refresh: bool = False) -> dict[str, ModuleType]:
    """Descubre los módulos de `informes/` y los indexa por nombre.

    El nombre es el filename del módulo (sin .py). Módulos que empiezan
    con `_` se ignoran. Un módulo sin `construir_contexto` se ignora con
    warning en consola (no rompe el listado de los demás).
    """
    global _registry
    if _registry is not None and not refresh:
        return _registry

    from . import informes as informes_pkg

    registry: dict[str, ModuleType] = {}
    for info in pkgutil.iter_modules(informes_pkg.__path__):
        if info.name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"{informes_pkg.__name__}.{info.name}")
        except Exception as e:  # informe roto no debe tumbar el resto
            print(f"[reports.word] informe '{info.name}' no importable: {type(e).__name__}: {e}")
            continue
        if not callable(getattr(mod, "construir_contexto", None)):
            print(f"[reports.word] informe '{info.name}' sin construir_contexto — ignorado")
            continue
        registry[info.name] = mod

    _registry = registry
    return registry


def obtener_modulo(nombre: str) -> ModuleType:
    """Módulo del informe `nombre`. KeyError con mensaje útil si no existe."""
    registry = get_registry()
    if nombre not in registry:
        raise KeyError(
            f"Informe Word '{nombre}' no registrado. "
            f"Disponibles: {sorted(registry) or '(ninguno)'}"
        )
    return registry[nombre]


def listar_informes() -> list[dict]:
    """Metadata de todos los informes registrados, para el frontend."""
    out = []
    for nombre, mod in sorted(get_registry().items()):
        plantilla = resolver_plantilla(mod)
        out.append({
            "nombre": nombre,
            "label": getattr(mod, "LABEL", nombre),
            "descripcion": getattr(mod, "DESCRIPCION", ""),
            "params_esperados": getattr(mod, "PARAMS_ESPERADOS", []),
            "plantilla": plantilla.name,
            "plantilla_existe": plantilla.exists(),
        })
    return out
