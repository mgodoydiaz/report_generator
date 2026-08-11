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

**Básica antes que media.** El nivel se normaliza al "grado" del sistema
chileno: la básica ocupa 1–8 y la media se desplaza a 9–12 (I° medio =
9, IV° medio = 12). El desplazamiento se aplica cuando el nivel viene en
romanos (notación exclusiva de la media) o cuando el texto dice MEDIO /
MEDIA. Sin esto, "1 A" y "I A" colisionaban en el mismo nivel y un
informe con básica y media mezcladas intercalaba los cursos
("1 A, I A, 2 A, II A…"), y "1° MEDIO" salía antes que "5° BÁSICO".

Ejemplo:
    >>> sorted(["III°A", "I°B", "II°C", "I°A"], key=curso_sort_key)
    ['I°A', 'I°B', 'II°C', 'III°A']
    >>> sorted(["I A", "2 A", "1 A"], key=curso_sort_key)
    ['1 A', '2 A', 'I A']
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

# La básica ocupa los niveles 1–8, así que la media arranca en 9
# (I° medio = 9, IV° medio = 12) y queda siempre después.
_OFFSET_MEDIA = 8

# "1° MEDIO", "2 medio B", "Enseñanza Media"… El límite de palabra evita
# falsos positivos tipo "PROMEDIO" o un paralelo "MA".
_RE_MEDIA = re.compile(r"\bMEDI[AO]S?\b", re.IGNORECASE)


def curso_sort_key(curso: str) -> Tuple[int, str]:
    """Devuelve una tupla ordenable (nivel_num, letra_paralelo).

    `nivel_num` es el grado del sistema chileno: 1–8 para la básica y
    9–12 para la media (I° medio = 9), de modo que toda la básica va
    antes que toda la media.

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
    # Resolver número. El romano es notación exclusiva de la media, así que
    # ya trae el desplazamiento implícito; el arábigo solo se desplaza si el
    # texto dice MEDIO/MEDIA (BÁSICO y el caso sin sufijo quedan en básica).
    if num_str.isdigit():
        nivel = int(num_str)
        if _RE_MEDIA.search(s):
            nivel += _OFFSET_MEDIA
    else:
        nivel = _ROMAN_TO_INT.get(num_str, 999)
        if nivel != 999:
            nivel += _OFFSET_MEDIA
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
