"""Evaluador seguro de expresiones de configuración (reemplazo de eval()).

Las reglas `math` de ModifyColumnValues traen `condicion`/`expresion` como
strings en el config_json del pipeline. Antes se evaluaban con `eval()`
(superficie de inyección: un config malicioso podía ejecutar código
arbitrario). Ahora se evalúan con simpleeval, que solo permite:

- Operadores aritméticos/booleanos/comparaciones y slicing.
- f-strings, listas/dicts/sets literales.
- Las funciones de `FUNCIONES_PERMITIDAS` (abs, round, str, hasattr, ...).
- Métodos públicos de los valores (str.split, Series.get, Timestamp.month...).
- `re.search/match/sub/...` vía un shim (los módulos reales están bloqueados).

Sin __import__, sin open, sin atributos privados, sin exec.
"""
from __future__ import annotations

import re as _re
from typing import Any, Mapping

from simpleeval import EvalWithCompoundTypes, InvalidExpression


class _ReSeguro:
    """Superficie mínima del módulo `re` para expresiones de config.

    simpleeval bloquea módulos reales; este objeto plano expone solo las
    funciones de matching/reemplazo (sin compile ni flags exóticos).
    """
    search = staticmethod(_re.search)
    match = staticmethod(_re.match)
    fullmatch = staticmethod(_re.fullmatch)
    findall = staticmethod(_re.findall)
    split = staticmethod(_re.split)
    sub = staticmethod(_re.sub)
    escape = staticmethod(_re.escape)
    IGNORECASE = _re.IGNORECASE


FUNCIONES_PERMITIDAS = {
    "abs": abs, "round": round, "min": min, "max": max,
    "sum": sum, "len": len, "str": str, "float": float, "int": int,
    "bool": bool, "hasattr": hasattr,
}


class ExpresionInvalida(ValueError):
    """La expresión de config no se pudo evaluar de forma segura."""


def evaluar_expresion(expresion: str, variables: Mapping[str, Any]) -> Any:
    """Evalúa una expresión de configuración en sandbox.

    Args:
        expresion: string tipo "round(x / 100, 2)" o
            "f\"{row['Fecha'].month:02d}\"".
        variables: nombres disponibles (ej {"x": 0.85} o {"row": serie}).

    Returns:
        El resultado de la expresión.

    Raises:
        ExpresionInvalida: si la expresión usa algo fuera del sandbox
            (imports, dunders, funciones no permitidas) o tiene sintaxis
            inválida. El mensaje incluye la expresión para debug del config.
    """
    evaluador = EvalWithCompoundTypes(
        functions=dict(FUNCIONES_PERMITIDAS),
        names={**variables, "re": _ReSeguro, "None": None, "True": True, "False": False},
    )
    try:
        return evaluador.eval(expresion)
    except InvalidExpression as e:
        raise ExpresionInvalida(
            f"Expresión no permitida o inválida: {expresion!r} — {e}. "
            f"Funciones disponibles: {sorted(FUNCIONES_PERMITIDAS)} + re.*"
        ) from e
    except SyntaxError as e:
        raise ExpresionInvalida(f"Sintaxis inválida en {expresion!r}: {e}") from e
