"""Utilidades HTTP compartidas entre routers."""
from __future__ import annotations

import unicodedata
from urllib.parse import quote


def content_disposition(filename: str, disposition: str = "attachment") -> str:
    """Valor de `Content-Disposition` seguro para nombres con tildes/ñ.

    Starlette codifica las cabeceras en latin-1, así que el `filename`
    clásico debe ser ASCII puro (RFC 6266): acá se translitera vía NFKD
    ("Cálculo" → "Calculo"). El nombre real, con sus caracteres UTF-8,
    viaja además en `filename*` percent-encoded (RFC 5987), que es el que
    los navegadores modernos usan para nombrar la descarga.
    """
    ascii_name = (
        unicodedata.normalize("NFKD", filename)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    # El fallback va entre comillas: fuera comillas, backslash y controles.
    ascii_name = "".join(
        c if c.isprintable() and c not in '"\\' else "_" for c in ascii_name
    ) or "descarga"
    header = f'{disposition}; filename="{ascii_name}"'
    if ascii_name != filename:
        header += f"; filename*=UTF-8''{quote(filename, safe='')}"
    return header
