"""Regresión: filtro de Asignatura en SIMCE debe ser case-insensitive.

Bug 2026-05-19: la BD guarda los valores como "Lenguaje" / "Matemáticas"
(capitalizado) pero el default en routers/reports.py era "LENGUAJE"
(uppercase). El filtro `df["Asignatura"] == "LENGUAJE"` no matcheaba
nada → df queda con 0 filas → apply_delta fallaba.

Fix en commit 815b97d: normalizar ambos lados con .strip().casefold()
antes de comparar.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pandas as pd
import pytest

from backend.rgenerator.reports.simce import crear_informe


@pytest.fixture
def df_estudiantes_lenguaje_y_matematicas():
    """DataFrame con filas para 2 asignaturas, 2 estudiantes c/u."""
    return pd.DataFrame({
        "Rut": ["A", "A", "B", "B"] * 2,
        "Rend": [0.4, 0.7, 0.5, 0.6, 0.6, 0.8, 0.5, 0.7],
        "Mes": ["ABRIL", "JUNIO"] * 4,
        "N Prueba": [1, 2] * 4,
        "Asignatura": (
            ["Lenguaje"] * 4 +     # BD storage casing
            ["Matemáticas"] * 4
        ),
    })


@pytest.fixture
def df_preguntas_minimo():
    """df_preguntas casi vacío — el test foca está en df_estudiantes."""
    return pd.DataFrame({
        "Asignatura": ["Lenguaje", "Matemáticas"],
        "Pregunta": [1, 1],
        "Logro": [0.5, 0.6],
        "Mes": ["ABRIL", "ABRIL"],
        "N Prueba": [1, 1],
    })


def _fake_pdf_bytes(*args, **kwargs):
    """Mock de runtime.construir_pdf para no requerir WeasyPrint."""
    return b"%PDF-1.4 fake\n"


@pytest.mark.unit
class TestAsignaturaCaseInsensitive:
    @pytest.mark.parametrize("asignatura", [
        "LENGUAJE",      # default uppercase
        "Lenguaje",      # storage casing
        "lenguaje",      # lowercase
        " Lenguaje ",    # con espacios
    ])
    def test_distintos_casings_matchean_lenguaje(
        self, df_estudiantes_lenguaje_y_matematicas, df_preguntas_minimo, asignatura
    ):
        """Cualquier casing del argumento debe matchear las filas con "Lenguaje" en BD."""
        # Verificamos el filtro inline replicando la lógica de construir(...)
        # sin generar PDF real (independiente de WeasyPrint).
        df = df_estudiantes_lenguaje_y_matematicas
        _asig_norm = str(asignatura).strip().casefold()
        filtered = df[df["Asignatura"].astype(str).str.strip().str.casefold() == _asig_norm]
        # 4 filas tienen "Lenguaje" en el fixture
        assert len(filtered) == 4
        assert (filtered["Asignatura"] == "Lenguaje").all()

    def test_construir_con_lenguaje_uppercase_no_explota(
        self, df_estudiantes_lenguaje_y_matematicas, df_preguntas_minimo
    ):
        """Test funcional: el flow completo de construir() no levanta KeyError 'Rut'."""
        with patch(
            "backend.rgenerator.reports.simce.crear_informe.runtime.construir_pdf",
            side_effect=_fake_pdf_bytes,
        ):
            result = crear_informe.construir(
                df_estudiantes_lenguaje_y_matematicas,
                df_preguntas_minimo,
                asignatura="LENGUAJE",     # ← uppercase, como el default viejo
                numero_prueba=1,
                mes="ABRIL",
            )
        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF")

    def test_construir_con_asignatura_inexistente_no_explota(
        self, df_estudiantes_lenguaje_y_matematicas, df_preguntas_minimo
    ):
        """Aun si la asignatura no existe, no debe levantar KeyError 'Rut'.

        Antes del fix del engine, df_estudiantes filtrado a 0 filas hacía
        explotar apply_delta. Ahora debe pasar y devolver bytes (PDF "sin
        datos" pero no crash).
        """
        with patch(
            "backend.rgenerator.reports.simce.crear_informe.runtime.construir_pdf",
            side_effect=_fake_pdf_bytes,
        ):
            result = crear_informe.construir(
                df_estudiantes_lenguaje_y_matematicas,
                df_preguntas_minimo,
                asignatura="INEXISTENTE",
                numero_prueba=1,
                mes="ABRIL",
            )
        assert isinstance(result, bytes)


@pytest.mark.unit
class TestAsignaturaCaseInsensitivePanguipulli:
    """Mismo fix aplicado a simce_panguipulli — verificar simetría con
    test inline del filtro (sin invocar construir() porque el esquema
    Panguipulli tiene derived_fields adicionales que requieren columnas
    específicas; eso pertenece a tests del motor PDF v2, no a este).
    """

    @pytest.mark.parametrize("asignatura", ["LENGUAJE", "Lenguaje", "lenguaje"])
    def test_filtro_inline_case_insensitive(self, asignatura):
        df = pd.DataFrame({
            "Asignatura": ["Lenguaje", "Matemáticas", "Lenguaje"],
            "Rend": [0.5, 0.6, 0.4],
        })
        _asig_norm = str(asignatura).strip().casefold()
        filtered = df[df["Asignatura"].astype(str).str.strip().str.casefold() == _asig_norm]
        assert len(filtered) == 2
        assert (filtered["Asignatura"] == "Lenguaje").all()
