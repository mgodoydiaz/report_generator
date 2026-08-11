"""Colores semánticos de los niveles de logro (motor de informes PDF v2).

Problema que resuelve
---------------------
Los gráficos de niveles cualitativos pintaban por POSICIÓN: el primer nivel
de `lista_niveles` se llevaba el primer color de la paleta, el segundo el
segundo, etc. Eso tiene dos consecuencias malas:

1. Basta invertir el orden de `lista_niveles` en un esquema para que el
   semáforo salga al revés (Inicial verde, Avanzado rojo).
2. La paleta heredada del LaTeX (`#1f9e89` verde-agua, `#f1a340` naranja,
   `#e64b35` tomate) no es el rojo/amarillo/verde que la fundación asocia a
   los niveles ni el que muestra `/indicadores`
   (`Indicator.achievement_levels` de DIA: Inicial `#dc2626`, Intermedio
   `#eab308`, Avanzado `#22c55e`). El mismo nivel se veía de dos colores
   distintos según qué pantalla abriera el usuario — P1-5 del QA
   2026-08-03 (`docs/reportes/qa_informes_2026-08-03/dia.md`).

Aquí el color se decide por el NOMBRE del nivel, no por su posición, y la
escala es la oficial (rojo → amarillo → verde) suavizada a tonos pastel:
los informes se imprimen y los colores saturados dejan las etiquetas
ilegibles y las páginas ruidosas. Todos los tonos de la escala admiten el
texto oscuro de `charts.color_texto_sobre` con contraste WCAG AA (≥ 4.5:1).

Precedencia de color (de mayor a menor), implementada en
`colores_para_niveles`:

1. `color_overrides` — inyección explícita del llamador. Es la vía por la
   que un informe hereda `Indicator.achievement_levels` tal cual.
2. `lista_paleta` — paleta posicional explícita del esquema/llamador.
3. Mapa semántico por nombre (este módulo).
4. Escala pastel por posición, como último recurso para nombres
   desconocidos.

Alcance: `reports/charts.py`. El motor v1 (`core/report_steps.py`,
`PALETTE_SEMAFORO`) conserva su paleta LaTeX y no se toca.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable, Mapping, Sequence

__all__ = [
    "ROJO_PASTEL",
    "NARANJA_PASTEL",
    "AMARILLO_PASTEL",
    "LIMA_PASTEL",
    "VERDE_PASTEL",
    "COLORES_NIVEL_LOGRO",
    "ESCALAS_PASTEL",
    "normalizar_nivel",
    "color_semantico_nivel",
    "escala_pastel",
    "colores_para_niveles",
]


# ─────────────────────────────────────────────────────────────────────────
# La escala
# ─────────────────────────────────────────────────────────────────────────

#: Peor desempeño. Pastel del `#dc2626` oficial.
ROJO_PASTEL = "#e57373"
#: Escalón intermedio-bajo. Solo aparece con 4 o 5 niveles (ej IDEL).
NARANJA_PASTEL = "#efa06b"
#: Escalón medio. Pastel del `#eab308` oficial.
AMARILLO_PASTEL = "#f6d55c"
#: Escalón intermedio-alto. Solo aparece con 5 niveles.
LIMA_PASTEL = "#b5d46e"
#: Mejor desempeño. Pastel del `#22c55e` oficial.
VERDE_PASTEL = "#81c784"


#: Escalas por cantidad de niveles, siempre de PEOR a MEJOR.
ESCALAS_PASTEL: dict[int, list[str]] = {
    1: [VERDE_PASTEL],
    2: [ROJO_PASTEL, VERDE_PASTEL],
    3: [ROJO_PASTEL, AMARILLO_PASTEL, VERDE_PASTEL],
    4: [ROJO_PASTEL, NARANJA_PASTEL, AMARILLO_PASTEL, VERDE_PASTEL],
    5: [ROJO_PASTEL, NARANJA_PASTEL, AMARILLO_PASTEL, LIMA_PASTEL, VERDE_PASTEL],
}


#: Nombre normalizado del nivel → color. Las claves se escriben ya
#: normalizadas (minúsculas, sin tildes, espacios colapsados): el lookup
#: pasa por `normalizar_nivel`, así que "Medianamente Logrado",
#: "medianamente  logrado" y "MEDIANAMENTE LOGRADO" caen en la misma
#: entrada.
#:
#: Familias cubiertas:
#: - DIA        : Inicial / Intermedio / Avanzado  (`dia/esquema.json`)
#: - SIMCE      : Insuficiente / Elemental / Adecuado
#: - Logro      : No Logrado / Medianamente Logrado / Logrado
#: - IDEL (4)   : Crítico / Alto Riesgo / Cierto Riesgo / Bajo Riesgo
COLORES_NIVEL_LOGRO: dict[str, str] = {
    # ── DIA ──────────────────────────────────────────────────────────
    "inicial": ROJO_PASTEL,
    "intermedio": AMARILLO_PASTEL,
    "avanzado": VERDE_PASTEL,
    # ── SIMCE ────────────────────────────────────────────────────────
    "insuficiente": ROJO_PASTEL,
    "elemental": AMARILLO_PASTEL,
    "adecuado": VERDE_PASTEL,
    # ── Escala "logrado" ─────────────────────────────────────────────
    "no logrado": ROJO_PASTEL,
    "por lograr": ROJO_PASTEL,
    "medianamente logrado": AMARILLO_PASTEL,
    "parcialmente logrado": AMARILLO_PASTEL,
    "logrado": VERDE_PASTEL,
    # ── IDEL (riesgo, 4 niveles) ─────────────────────────────────────
    # Ojo con el orden: en esta familia "Bajo Riesgo" es el MEJOR nivel.
    # Por eso el mapa es por nombre completo y no por la palabra suelta.
    "critico": ROJO_PASTEL,
    "alto riesgo": NARANJA_PASTEL,
    "cierto riesgo": AMARILLO_PASTEL,
    "bajo riesgo": VERDE_PASTEL,
    "sin riesgo": VERDE_PASTEL,
}


_RE_ESPACIOS = re.compile(r"\s+")


def normalizar_nivel(nombre: Any) -> str:
    """Clave de lookup de un nombre de nivel.

    Minúsculas, sin tildes ni diacríticos, espacios colapsados y sin
    espacios al borde. "Crítico" y "CRITICO " dan la misma clave.
    """
    s = unicodedata.normalize("NFKD", str(nombre))
    s = s.encode("ascii", "ignore").decode("ascii")
    return _RE_ESPACIOS.sub(" ", s).strip().lower()


def color_semantico_nivel(nombre: Any) -> str | None:
    """Color pastel del nivel `nombre`, o None si no es un nivel conocido.

    Ejemplos:
        >>> color_semantico_nivel("Inicial")
        '#e57373'
        >>> color_semantico_nivel("  AVANZADO ")
        '#81c784'
        >>> color_semantico_nivel("Crítico")
        '#e57373'
        >>> color_semantico_nivel("Eje Temático") is None
        True
    """
    if nombre is None:
        return None
    return COLORES_NIVEL_LOGRO.get(normalizar_nivel(nombre))


def escala_pastel(n_niveles: int, *, mejor_primero: bool = False) -> list[str]:
    """Escala pastel de `n_niveles` colores.

    Args:
        n_niveles: cantidad de niveles. Fuera de 1–5 devuelve la escala de
            5 (los llamadores ciclan con `% len`).
        mejor_primero: True si la lista de niveles del llamador va de MEJOR
            a PEOR (el caso de `alumnos_por_nivel_cualitativo` y
            `composicion_por_nivel`).
    """
    base = ESCALAS_PASTEL.get(n_niveles, ESCALAS_PASTEL[5])
    return list(reversed(base)) if mejor_primero else list(base)


def colores_para_niveles(
    niveles: Sequence[Any],
    *,
    lista_paleta: Iterable[str] | None = None,
    color_overrides: Mapping[Any, str] | None = None,
    mejor_primero: bool = True,
    paleta_fallback: Sequence[str] | None = None,
) -> dict[Any, str]:
    """`{nivel: color}` resolviendo la precedencia documentada arriba.

    Args:
        niveles: niveles en el orden en que los declara el llamador.
        lista_paleta: paleta posicional explícita. Si viene, gana sobre el
            mapa semántico (el llamador sabe lo que quiere).
        color_overrides: `{nivel: "#rrggbb"}`. Máxima precedencia. Se
            matchea por nombre normalizado, así que un override escrito
            "Crítico" pisa un nivel que en los datos viene "CRITICO".
        mejor_primero: True si `niveles` va de mejor a peor. Solo afecta al
            fallback posicional.
        paleta_fallback: escala posicional para los nombres que el mapa
            semántico no conoce. Por defecto, `escala_pastel`.

    Returns:
        dict con una entrada por nivel, en el mismo orden de `niveles`.
    """
    lista = list(niveles)
    paleta_explicita = list(lista_paleta) if lista_paleta else None
    fallback = list(paleta_fallback) if paleta_fallback else escala_pastel(
        len(lista), mejor_primero=mejor_primero
    )

    overrides_norm: dict[str, str] = {}
    for nivel, color in (color_overrides or {}).items():
        if color:
            overrides_norm[normalizar_nivel(nivel)] = color

    resultado: dict[Any, str] = {}
    for i, nivel in enumerate(lista):
        clave = normalizar_nivel(nivel)
        if clave in overrides_norm:
            resultado[nivel] = overrides_norm[clave]
            continue
        if paleta_explicita:
            resultado[nivel] = paleta_explicita[i % len(paleta_explicita)]
            continue
        semantico = COLORES_NIVEL_LOGRO.get(clave)
        if semantico:
            resultado[nivel] = semantico
            continue
        resultado[nivel] = fallback[i % len(fallback)] if fallback else "#888888"
    return resultado
