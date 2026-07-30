"""Registro de informes CUSTOM — hardcodeados en Python, uno por archivo.

Un "informe custom" es un informe cuyo layout NO se configura desde la UI
(Editor de Layout) sino que está escrito a mano en Python: SIMCE oficial,
DIA, PDL IDEL-Woodcock, etc. Cada informe es UN módulo en esta carpeta y
el nombre del archivo ES su identificador público:

    POST /api/reports/custom/<nombre>

El registro se auto-descubre (mismo patrón que `reports/word/`): agregar un
archivo acá lo publica en el selector "Generar informe" del frontend sin
tocar routers ni frontend.

Contrato del módulo (ver `_ejemplo.py` para la plantilla comentada):

    LABEL = "Informe PDL IDEL-Woodcock"     # obligatorio
    DESCRIPCION = "..."                      # obligatorio
    FORMATO = "pdf"                          # "pdf" | "word"
    ENGINE_TYPES = ["pdl_idel"]              # None → aplica a todos
    REQUIERE_FILTRO_TEMPORAL = []            # ej ["Mes", "N Prueba"]
    REQUIERE_ASIGNATURA = False              # True → el informe es por asignatura
    FILENAME = "informe_pdl_idel.pdf"        # opcional
    MODOS = ["ultima_prueba", "anual"]       # modos de período que sabe generar
    MOTIVO_MODO_NO_DISPONIBLE = {...}        # {modo: motivo pedagógico}

    def generar(db, *, indicator_id, org_id, modo=None, filtros=None,
                params=None, overrides=None) -> bytes: ...

`MODOS` es lo que convierte a un módulo en un informe del MOTOR ÚNICO: el
despacho de `POST /api/indicators/{id}/export-pdf` le entrega las cards de
período que el módulo declara y deja de usar el `pdf_layout`. Un módulo sin
`MODOS` (o con la lista vacía) se comporta exactamente como antes: solo
"formato oficial" vía `POST /api/reports/custom/{nombre}`.

API pública:
    get_registry(refresh=False)  → dict {nombre: módulo}
    obtener_modulo(nombre)       → módulo o KeyError
    listar_informes()            → metadata para el frontend
    aplica_a(modulo, engine_type)→ bool (filtro por ENGINE_TYPES)
    requiere_asignatura(modulo)  → bool (lee REQUIERE_ASIGNATURA)
    metadata(nombre|modulo)      → dict de UN informe
    modos(modulo)                → list[str] de modos declarados
    soporta_modo(modulo, modo)   → bool
    motivo_modo(modulo, modo)    → motivo pedagógico del modo no servido
    nombre_de(modulo)            → nombre público del módulo
    modulo_de_indicador(engine_type) → módulo del motor único, o None
"""
from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType
from typing import Optional

MIME_POR_FORMATO = {
    "pdf": "application/pdf",
    "word": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

#: Motivo genérico cuando un módulo declara `MODOS` pero no explica por qué
#: le falta uno. Se prefiere SIEMPRE el motivo pedagógico del módulo.
MOTIVO_MODO_GENERICO = "Este indicador no genera este informe."

_registry: dict[str, ModuleType] | None = None


def get_registry(refresh: bool = False) -> dict[str, ModuleType]:
    """Descubre los módulos de informe de esta carpeta y los indexa por nombre.

    El nombre es el filename del módulo (sin .py). Módulos que empiezan con
    `_` se ignoran (helpers y plantillas). Un módulo sin `generar` callable
    se ignora con warning. Un módulo roto no tumba el resto del registro.
    """
    global _registry
    if _registry is not None and not refresh:
        return _registry

    registry: dict[str, ModuleType] = {}
    for info in pkgutil.iter_modules(__path__):
        if info.name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"{__name__}.{info.name}")
        except Exception as e:  # informe roto no debe tumbar el resto
            print(f"[reports.custom] informe '{info.name}' no importable: {type(e).__name__}: {e}")
            continue
        if not callable(getattr(mod, "generar", None)):
            print(f"[reports.custom] informe '{info.name}' sin generar() — ignorado")
            continue
        registry[info.name] = mod

    _registry = registry
    return registry


def obtener_modulo(nombre: str) -> ModuleType:
    """Módulo del informe `nombre`. KeyError con mensaje útil si no existe."""
    registry = get_registry()
    if nombre not in registry:
        raise KeyError(
            f"Informe custom '{nombre}' no registrado. "
            f"Disponibles: {sorted(registry) or '(ninguno)'}"
        )
    return registry[nombre]


def nombre_archivo(nombre: str, mod: ModuleType) -> str:
    """FILENAME del módulo, o `informe_<nombre>.<ext>` por defecto."""
    declarado = getattr(mod, "FILENAME", None)
    if declarado:
        return str(declarado)
    ext = "docx" if getattr(mod, "FORMATO", "pdf") == "word" else "pdf"
    return f"informe_{nombre}.{ext}"


def metadata(nombre: str, mod: ModuleType | None = None) -> dict:
    """Metadata de UN informe registrado (para el frontend)."""
    mod = mod or obtener_modulo(nombre)
    formato = getattr(mod, "FORMATO", "pdf")
    return {
        "nombre": nombre,
        "label": getattr(mod, "LABEL", nombre),
        "descripcion": getattr(mod, "DESCRIPCION", ""),
        "formato": formato,
        "mime": MIME_POR_FORMATO.get(formato, "application/octet-stream"),
        "engine_types": getattr(mod, "ENGINE_TYPES", None),
        "requiere_filtro_temporal": list(getattr(mod, "REQUIERE_FILTRO_TEMPORAL", []) or []),
        "requiere_asignatura": requiere_asignatura(mod),
        "filename": nombre_archivo(nombre, mod),
        # Motor único (contrato N2): vacío en los módulos que solo sirven el
        # informe "formato oficial" — no cambia nada para ellos.
        "modos": modos(mod),
        "motivos_modo": dict(getattr(mod, "MOTIVO_MODO_NO_DISPONIBLE", {}) or {}),
    }


def requiere_asignatura(mod: ModuleType) -> bool:
    """True si el informe declara `REQUIERE_ASIGNATURA` (ausente → False).

    El módulo solo DECLARA que su informe es por asignatura; quién decide
    si hay que pedirla es el dato (report-options la publica cuando el
    indicador trae ≥2 asignaturas) y quién la exige es el motor
    (`dispatch_v2`, igual que con `REQUIERE_FILTRO_TEMPORAL`).
    """
    return bool(getattr(mod, "REQUIERE_ASIGNATURA", False))


def listar_informes() -> list[dict]:
    """Metadata de todos los informes registrados, ordenada por nombre."""
    return [metadata(nombre, mod) for nombre, mod in sorted(get_registry().items())]


def aplica_a(mod: ModuleType, engine_type: Optional[str]) -> bool:
    """True si el informe corresponde al `engine_type` del indicador.

    `ENGINE_TYPES = None` (o ausente) significa "aplica a todos los
    indicadores". Una lista restringe a esos engine_types.
    """
    permitidos = getattr(mod, "ENGINE_TYPES", None)
    if permitidos is None:
        return True
    return engine_type in permitidos


def informes_para(engine_type: Optional[str]) -> list[dict]:
    """Metadata de los informes aplicables a `engine_type`."""
    return [
        metadata(nombre, mod)
        for nombre, mod in sorted(get_registry().items())
        if aplica_a(mod, engine_type)
    ]


# ─────────────────────────────────────────────────────────────────────────
# Motor único: modos de período que sabe generar cada módulo (contrato N2)
# ─────────────────────────────────────────────────────────────────────────

def modos(mod: ModuleType) -> list[str]:
    """Modos de período declarados por el módulo.

    `[]` (ausente o vacío) ⇒ retrocompatibilidad total: el módulo sigue
    siendo solo "formato oficial" y las cards de período usan el path v1.
    """
    return list(getattr(mod, "MODOS", []) or [])


def soporta_modo(mod: ModuleType, modo: Optional[str]) -> bool:
    """True si `modo` está en `MODOS`.

    `modo=None` devuelve False a propósito: `None` es el informe "formato
    oficial" clásico (`POST /api/reports/custom/{nombre}`), no un modo de
    período.
    """
    if not modo:
        return False
    return modo in modos(mod)


def motivo_modo(mod: ModuleType, modo: str) -> str:
    """Motivo pedagógico por el que el módulo no sirve `modo`."""
    motivos = getattr(mod, "MOTIVO_MODO_NO_DISPONIBLE", {}) or {}
    return motivos.get(modo) or MOTIVO_MODO_GENERICO


def nombre_de(mod: ModuleType) -> str:
    """Nombre público del módulo (el filename sin .py)."""
    return mod.__name__.rsplit(".", 1)[-1]


def modulo_de_indicador(engine_type: Optional[str]) -> Optional[ModuleType]:
    """Módulo del motor único que atiende a ese `engine_type`.

    Es el único módulo registrado que `aplica_a(engine_type)` **y** declara
    `MODOS`. Devuelve None cuando no hay ninguno (el despacho cae al path
    v1, que es el comportamiento actual). Con más de uno gana el primero por
    orden alfabético y se loguea un warning: dos módulos del motor único
    para el mismo engine_type es un error de configuración.
    """
    candidatos = [
        (nombre, mod)
        for nombre, mod in sorted(get_registry().items())
        if aplica_a(mod, engine_type) and modos(mod)
    ]
    if not candidatos:
        return None
    if len(candidatos) > 1:
        print(
            f"[reports.custom] engine_type '{engine_type}' tiene "
            f"{len(candidatos)} módulos con MODOS "
            f"({', '.join(n for n, _ in candidatos)}); se usa el primero"
        )
    return candidatos[0][1]
