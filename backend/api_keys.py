"""
api_keys.py — Crypto de API keys para ingesta externa (W1).

Responsabilidades:
  - Generar keys con formato `rg_live_<prefix4><aleatorio>` (secreto en claro
    entregado UNA sola vez al crear).
  - Hashear/verificar el secreto con bcrypt.
  - Serializar/deserializar `scopes` (JSON array almacenado en Text).

Regla de oro: el secreto en claro NUNCA se persiste ni se loguea. La DB solo
guarda el hash bcrypt (`key_hash`) y el `prefix` visible.

La dependency de auth (`get_org_from_api_key`, `require_scope`) vive en
`backend/auth.py` para mantener toda la superficie de autenticación en un
mismo lugar; este módulo es solo crypto/serialización sin FastAPI.
"""
from __future__ import annotations

import hashlib
import json
import secrets
from typing import List, Tuple

import bcrypt as _bcrypt

# Prefijo de "environment" de la key. Estilo Stripe (`rg_live_...`). Podría
# extenderse a `rg_test_` en el futuro; por ahora todas son "live".
KEY_ENV_PREFIX = "rg_live_"

# Chars aleatorios que quedan visibles en el `prefix` después de `rg_live_`.
# El prefix total (`rg_live_a1b2`) cabe en String(12) del modelo.
_PREFIX_RANDOM_CHARS = 4

# Bytes de entropía del secreto aleatorio. token_urlsafe(32) ≈ 43 chars.
_SECRET_ENTROPY_BYTES = 32


def _sha256_hex(secreto_claro: str) -> bytes:
    """Pre-hash sha256 (hex, 64 bytes ASCII) del secreto.

    bcrypt trunca silenciosamente a 72 bytes. Nuestro secreto completo
    (`rg_live_` + prefix + ~43 chars aleatorios) puede acercarse a ese
    límite, y si algún día se alarga, la verificación seguiría "funcionando"
    ignorando la cola — un riesgo de seguridad sutil. Pre-hasheamos con
    sha256 a un digest hex de longitud fija (64 bytes) que siempre entra en
    los 72 bytes de bcrypt, eliminando la truncación como variable.
    """
    return hashlib.sha256(secreto_claro.encode("utf-8")).hexdigest().encode("ascii")


def generar_api_key() -> Tuple[str, str, str]:
    """Genera una nueva API key.

    Returns:
        (secreto_claro, prefix, key_hash)
        - `secreto_claro`: la key completa `rg_live_<prefix4><aleatorio>`.
          Se entrega al cliente UNA sola vez; nunca se persiste.
        - `prefix`: parte visible (`rg_live_a1b2`, ≤12 chars) para identificar
          la key en la UI/listados sin revelar el secreto.
        - `key_hash`: bcrypt(sha256(secreto_claro)) — lo único que se guarda.
    """
    # 4 chars url-safe visibles para el prefix identificador.
    prefix_random = secrets.token_urlsafe(6)[:_PREFIX_RANDOM_CHARS]
    prefix = f"{KEY_ENV_PREFIX}{prefix_random}"

    # Cola aleatoria con >=32 bytes de entropía.
    aleatorio = secrets.token_urlsafe(_SECRET_ENTROPY_BYTES)
    secreto_claro = f"{prefix}{aleatorio}"

    key_hash = hashear_api_key(secreto_claro)
    return secreto_claro, prefix, key_hash


def hashear_api_key(secreto_claro: str) -> str:
    """Devuelve el hash bcrypt del secreto (pre-hasheado con sha256)."""
    return _bcrypt.hashpw(_sha256_hex(secreto_claro), _bcrypt.gensalt()).decode()


def verificar_api_key(secreto_claro: str, key_hash: str) -> bool:
    """Verifica el secreto en claro contra su hash bcrypt.

    Devuelve False (en vez de propagar) ante hashes malformados para que un
    registro corrupto no tumbe la request de auth.
    """
    try:
        return _bcrypt.checkpw(_sha256_hex(secreto_claro), key_hash.encode())
    except (ValueError, TypeError):
        return False


def extraer_prefix(secreto_claro: str) -> str:
    """Deriva el `prefix` (`rg_live_a1b2`) de un secreto en claro.

    Se usa en el flujo de auth para localizar la fila candidata por índice
    sin escanear toda la tabla ni tener que verificar contra cada hash.
    """
    return secreto_claro[: len(KEY_ENV_PREFIX) + _PREFIX_RANDOM_CHARS]


# ─── Scopes (serialización JSON) ─────────────────────────────

def serializar_scopes(scopes: List[str]) -> str:
    """Lista de scopes → string JSON para almacenar en Text."""
    return json.dumps(list(scopes or []), ensure_ascii=False)


def deserializar_scopes(scopes_json: str) -> List[str]:
    """String JSON almacenado → lista de scopes. Tolerante a null/corrupto."""
    if not scopes_json:
        return []
    try:
        data = json.loads(scopes_json)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    return [str(s) for s in data]
