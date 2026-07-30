"""Guardia anti-branding personal en los esquemas de informes.

Los informes se entregan a fundaciones: el pie de página y el autor deben
identificar a la ORGANIZACIÓN dueña de los datos, nunca al desarrollador.
Históricamente los esquemas traían "Miguel Godoy Díaz" hardcodeado en
`variables_documento.leftfooter` / `.theauthor`; hoy quedan vacíos y el
runtime resuelve el nombre de la org (`report_steps.resolver_nombre_organizacion`
y `reports/dispatch_v2.aplicar_pie_organizacion`).

Este test falla si alguien reintroduce el nombre personal en un esquema.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent

# Directorios de esquemas/plantillas de configuración que se entregan al
# cliente. Solo se auditan .json: el resto del repo puede mencionar al autor
# legítimamente (pyproject, README, docs).
_DIRS_AUDITADOS = (
    "backend/schemas",
    "backend/rgenerator/reports",
    "data/database/reports_templates",
)

_PATRON_NOMBRE_PERSONAL = re.compile(r"godoy", re.IGNORECASE)

# Claves que definen el pie/autor del informe: deben quedar vacías para que
# el runtime inyecte el nombre de la organización.
_CLAVES_PIE = ("leftfooter", "theauthor", "left_footer")


def _jsons_auditados():
    for base in _DIRS_AUDITADOS:
        directorio = ROOT / base
        if not directorio.exists():
            continue
        for path in directorio.rglob("*.json"):
            if "__pycache__" in path.parts:
                continue
            yield path


@pytest.mark.unit
def test_ningun_esquema_json_trae_nombre_personal():
    infractores = []
    for path in _jsons_auditados():
        contenido = path.read_text(encoding="utf-8")
        for m in _PATRON_NOMBRE_PERSONAL.finditer(contenido):
            linea = contenido.count("\n", 0, m.start()) + 1
            infractores.append(f"{path.relative_to(ROOT)}:{linea}")
    assert not infractores, (
        "Nombre personal hardcodeado en esquemas de informe. Dejar el pie/autor "
        "vacío: el backend cae al nombre de la organización.\n  "
        + "\n  ".join(infractores)
    )


@pytest.mark.unit
def test_pie_y_autor_de_los_esquemas_estan_vacios():
    """`leftfooter` / `theauthor` / `left_footer` deben venir vacíos.

    Cualquier valor por defecto sería el mismo para todas las organizaciones,
    que es justo el bug que este módulo previene.
    """

    def _recorrer(nodo, path: Path, ruta: str = ""):
        if isinstance(nodo, dict):
            for clave, valor in nodo.items():
                sub = f"{ruta}.{clave}" if ruta else clave
                if clave in _CLAVES_PIE and str(valor or "").strip():
                    yield f"{path.relative_to(ROOT)} → {sub} = {valor!r}"
                else:
                    yield from _recorrer(valor, path, sub)
        elif isinstance(nodo, list):
            for i, item in enumerate(nodo):
                yield from _recorrer(item, path, f"{ruta}[{i}]")

    infractores = []
    for path in _jsons_auditados():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        infractores.extend(_recorrer(data, path))

    assert not infractores, (
        "Pie/autor con valor fijo en esquemas de informe (debe quedar vacío "
        "para que el runtime use el nombre de la organización):\n  "
        + "\n  ".join(infractores)
    )
