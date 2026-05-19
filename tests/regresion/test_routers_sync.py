"""Regresión: routers críticos deben ser `def` (no `async def`).

Bug 2026-05-19: handlers `async def` con SQLAlchemy sync bloquean el
event loop. Con 1 worker en Railway eso serializaba todos los requests.

Fix en commit 781c12a: convertir todos los handlers de results, charts,
tables, indicators a sync `def`. FastAPI los despacha al threadpool.

Este test escanea los módulos por handlers `async def` y falla si
alguien revierte (o introduce uno nuevo) sin querer. Las rutas
auth+pipelines pueden ser async si lo justifican (background tasks),
pero los routers data-heavy NO.
"""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

# Módulos donde NO debe haber async def (handlers con SQLAlchemy sync)
SYNC_ONLY_ROUTERS = [
    "backend.routers.results",
    "backend.routers.charts",
    "backend.routers.tables",
    "backend.routers.indicators",
    "backend.routers.metrics",
    "backend.routers.reports",
]


def _has_await(node: ast.AST) -> bool:
    """True si el body de `node` contiene al menos un Await."""
    for child in ast.walk(node):
        if isinstance(child, ast.Await):
            return True
    return False


def _find_async_route_handlers(module_path: Path) -> list[str]:
    """Handlers decorados con @router.X que son `async def` SIN awaits internos.

    `async def` con awaits legítimos (ej file.read() de UploadFile) es válido —
    el problema es declarar async sin necesidad, eso bloquea el event loop con
    SQLAlchemy sync.
    """
    src = module_path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    bad = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        # ¿Está decorada con algo tipo @router.get / @router.post / ...?
        is_route = any(
            "router." in (ast.unparse(deco) if hasattr(ast, "unparse") else "")
            for deco in node.decorator_list
        )
        if is_route and not _has_await(node):
            bad.append(node.name)
    return bad


@pytest.mark.unit
@pytest.mark.parametrize("module_name", SYNC_ONLY_ROUTERS)
def test_router_no_tiene_handlers_async(module_name):
    """Los handlers de routers data-heavy deben ser `def`, no `async def`."""
    import importlib
    mod = importlib.import_module(module_name)
    module_path = Path(inspect.getfile(mod))
    bad = _find_async_route_handlers(module_path)
    assert not bad, (
        f"{module_name} tiene handlers async def: {bad}. "
        f"Deben ser `def` sync porque usan SQLAlchemy sin await — async def "
        f"bloquea el event loop y serializa requests. Ver commit 781c12a."
    )
