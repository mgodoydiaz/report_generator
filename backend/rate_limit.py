"""Limitador de intentos in-memory (ventana deslizante).

Pensado para el login: bloquea fuerza bruta de credenciales sin agregar
dependencias ni infraestructura. Vive en memoria del proceso — válido
mientras la app corra con --workers 1 (misma restricción documentada de
ACTIVE_RUNNERS). Si algún día hay múltiples workers, mover a Redis junto
con los runners.

Uso:
    limiter = SlidingWindowLimiter(max_attempts=5, window_seconds=900)
    if limiter.is_blocked(key): ...429...
    limiter.register_failure(key)   # tras credenciales inválidas
    limiter.reset(key)              # tras login exitoso
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    """Cuenta fallos por clave dentro de una ventana deslizante."""

    def __init__(self, max_attempts: int, window_seconds: float):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> None:
        q = self._failures[key]
        cutoff = now - self.window_seconds
        while q and q[0] < cutoff:
            q.popleft()
        if not q:
            self._failures.pop(key, None)

    def is_blocked(self, key: str) -> bool:
        """True si la clave acumuló max_attempts fallos dentro de la ventana."""
        now = time.time()
        with self._lock:
            self._prune(key, now)
            return len(self._failures.get(key, ())) >= self.max_attempts

    def register_failure(self, key: str) -> None:
        now = time.time()
        with self._lock:
            self._prune(key, now)
            self._failures[key].append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        """Borra todo el estado (usado por tests)."""
        with self._lock:
            self._failures.clear()

    def retry_after_seconds(self, key: str) -> int:
        """Segundos hasta que expire el fallo más antiguo de la ventana."""
        now = time.time()
        with self._lock:
            self._prune(key, now)
            q = self._failures.get(key)
            if not q or len(q) < self.max_attempts:
                return 0
            return max(1, int(q[0] + self.window_seconds - now))
