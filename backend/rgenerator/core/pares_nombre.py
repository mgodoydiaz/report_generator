"""Completado automático de pares de dimensiones `X` / `X_Norm`.

Convención del sistema: por cada dimensión de nombre `X` puede existir su
hermana normalizada `X_Norm` (típicamente `Nombre` / `Nombre_Norm`). Los
informes y los joins entre hitos usan una u otra según el caso, así que
**toda carga de datos debe dejar pobladas ambas columnas** cuando el par
está asociado a la métrica.

Este módulo es la fuente de verdad ÚNICA de esa red de seguridad. Lo usan
los cuatro caminos de escritura de `metric_data` de la aplicación:

- `backend/rgenerator/core/metric_steps.py` → `SaveToMetric` (pipelines).
- `backend/routers/metrics.py` → import CSV/Excel desde /values.
- `backend/routers/metrics.py` → alta manual de una fila.
- `backend/routers/ingest.py` → ingesta programática por API key (W1).

Si en el futuro aparece otro punto de inserción, debe importar de acá en
vez de reimplementar la lógica: si las implementaciones divergen, las
claves de join entre hitos dejan de coincidir.
"""
from __future__ import annotations

from typing import Dict, List, Mapping, Sequence, Tuple

from .derived_fields_engine import normalizar_nombre

#: Sufijos aceptados para la dimensión normalizada de un par.
SUFIJOS_NORM: Tuple[str, ...] = ("_Norm", "_norm", "_NORM")


def pares_nombre_normalizado(
    dim_name_to_id: Mapping[str, int]
) -> List[Tuple[int, int]]:
    """Pares (id_original, id_norm) de dimensiones tipo 'X' / 'X_Norm'.

    Convención del sistema: la dimensión normalizada se llama igual que
    la original más el sufijo `_Norm`. Ej: ('Nombre', 'Nombre_Norm').

    Solo devuelve pares donde AMBAS dimensiones están en el mapa recibido
    — es decir, ambas asociadas a la métrica destino. Una métrica que solo
    tiene `Nombre` (sin `Nombre_Norm`) no produce ningún par y por lo tanto
    no se toca.
    """
    pares: List[Tuple[int, int]] = []
    for nombre, dim_id in dim_name_to_id.items():
        for sufijo in SUFIJOS_NORM:
            id_norm = dim_name_to_id.get(f"{nombre}{sufijo}")
            if id_norm is not None:
                pares.append((dim_id, id_norm))
                break
    return pares


def completar_pares_nombre(
    dims_json: Dict[str, str],
    pares: Sequence[Tuple[int, int]],
) -> None:
    """Completa in-place la columna que falte de cada par nombre/normalizado.

    Red de seguridad para que TODA carga deje pobladas ambas columnas,
    sin depender de que el JSON del pipeline guardado en la DB traiga el
    mapeo correcto (ni de que el CSV que sube el usuario traiga las dos
    columnas):

    - Falta la normalizada y hay original → se normaliza con la función
      canónica (`normalizar_nombre`).
    - Falta la original y hay normalizada → se copia la normalizada. El
      original real ya se perdió (el archivo no lo traía o el pipeline no
      lo mapeó), pero es preferible mostrar el nombre reordenado a
      mostrar un vacío en los informes.
    - Si faltan ambas, la fila no tiene identidad y se deja intacta.

    NUNCA sobrescribe un valor ya presente: si las dos claves vienen con
    contenido, `dims_json` queda byte a byte igual.

    Los valores se leen con `str(...)` porque los caminos de API reciben
    JSON y una dimensión puede llegar como número o booleano.
    """
    for id_original, id_norm in pares:
        k_orig, k_norm = str(id_original), str(id_norm)
        val_orig = str(dims_json.get(k_orig) or "").strip()
        val_norm = str(dims_json.get(k_norm) or "").strip()
        if val_orig and not val_norm:
            normalizado = normalizar_nombre(val_orig)
            if normalizado:
                dims_json[k_norm] = normalizado
        elif val_norm and not val_orig:
            dims_json[k_orig] = val_norm


__all__ = [
    "SUFIJOS_NORM",
    "pares_nombre_normalizado",
    "completar_pares_nombre",
]
