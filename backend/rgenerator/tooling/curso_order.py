"""Ordenamiento canónico de cursos chilenos.

Los cursos en colegios chilenos se nombran con número (en romanos para
educación media, en arábigos o palabras para básica) + letra de paralelo.
El orden alfabético natural de Python rompe la lectura ("II°A" sale
después de "I°A" pero "III°A" sale antes de "II°A" por el segundo
carácter).

Este módulo provee `curso_sort_key(curso)` que devuelve una tupla
ordenable (nivel_num, letra) para usar como key en sort. Soporta:

    - Romanos (I°, II°, III°, IV°, V°, VI°, VII°, VIII°)
    - Arábigos (1°, 2°, ..., 8°)
    - Letras post-° (A, B, C, ..., MA, MB, P, etc.)
    - Cursos sin letra (I°, 7°)
    - Variantes con/sin espacios y mayúsculas/minúsculas

Ejemplo:
    >>> sorted(["III°A", "I°B", "II°C", "I°A"], key=curso_sort_key)
    ['I°A', 'I°B', 'II°C', 'III°A']
"""
from __future__ import annotations

import re
from typing import List, Tuple

# Mapping de romanos a ordinales. Soporta hasta VIII (8° medio).
_ROMAN_TO_INT = {
    "I": 1, "II": 2, "III": 3, "IV": 4,
    "V": 5, "VI": 6, "VII": 7, "VIII": 8,
}

# Regex que separa "número (romano o arábigo)" + "°" + "resto"
_CURSO_RE = re.compile(
    r"^\s*(?P<num>VIII|VII|VI|IV|III|II|I|V|\d+)\s*°?\s*(?P<resto>.*)$",
    re.IGNORECASE,
)


def curso_sort_key(curso: str) -> Tuple[int, str]:
    """Devuelve una tupla ordenable (nivel_num, letra_paralelo).

    Para cursos no parseables, devuelve (999, str(curso)) para que vayan
    al final en orden alfabético sin bloquear el sort.
    """
    if curso is None:
        return (999, "")
    s = str(curso).strip()
    if not s:
        return (999, "")
    m = _CURSO_RE.match(s)
    if not m:
        return (999, s)
    num_str = m.group("num").upper()
    resto = m.group("resto").strip().upper()
    # Resolver número
    if num_str.isdigit():
        nivel = int(num_str)
    else:
        nivel = _ROMAN_TO_INT.get(num_str, 999)
    # Letra del paralelo: si está vacía, usar "" (va antes de letras).
    return (nivel, resto)


def sort_cursos(cursos) -> List[str]:
    """Devuelve los cursos ordenados según `curso_sort_key`.

    Acepta cualquier iterable. Filtra valores None / vacíos.
    """
    return sorted(
        [c for c in cursos if c is not None and str(c).strip()],
        key=curso_sort_key,
    )
