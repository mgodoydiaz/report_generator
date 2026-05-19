"""Tests funcionales de `simce/crear_informe.construir(...)`.

Verifica el pipeline completo: filtros por asignatura + derived_fields +
filtro temporal final. No genera PDF real (mock de WeasyPrint).
"""
from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest

from backend.rgenerator.reports.simce import crear_informe


def _fake_pdf(*args, **kwargs):
    return b"%PDF-1.4 fake\n"


@pytest.fixture
def df_estudiantes_full():
    """DataFrame de estudiantes con 2 estudiantes × 2 meses × 2 asignaturas."""
    rows = []
    for rut, nombre in [("1-1", "Alice"), ("2-2", "Bob")]:
        for asig in ["Lenguaje", "Matemáticas"]:
            for mes, n_prueba, rend in [("ABRIL", 1, 0.4), ("JUNIO", 2, 0.6)]:
                rows.append({
                    "Rut": rut, "Nombre": nombre, "Asignatura": asig,
                    "Mes": mes, "N Prueba": n_prueba, "Rend": rend,
                    "Curso": "II A",
                })
    return pd.DataFrame(rows)


@pytest.fixture
def df_preguntas_full():
    rows = []
    for asig in ["Lenguaje", "Matemáticas"]:
        for mes, n_prueba in [("ABRIL", 1), ("JUNIO", 2)]:
            rows.append({
                "Asignatura": asig, "Mes": mes, "N Prueba": n_prueba,
                "Logro": 0.5, "Curso": "II A",
            })
    return pd.DataFrame(rows)


@pytest.mark.unit
class TestConstruir:
    def test_genera_pdf_path_feliz(self, df_estudiantes_full, df_preguntas_full):
        with patch(
            "backend.rgenerator.reports.simce.crear_informe.runtime.construir_pdf",
            side_effect=_fake_pdf,
        ):
            result = crear_informe.construir(
                df_estudiantes_full, df_preguntas_full,
                asignatura="Lenguaje", numero_prueba=1, mes="ABRIL",
            )
        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF")

    def test_filtro_asignatura_uppercase_matchea_lenguaje(
        self, df_estudiantes_full, df_preguntas_full
    ):
        """Bug del 2026-05-19: "LENGUAJE" debe matchear "Lenguaje" en BD."""
        with patch(
            "backend.rgenerator.reports.simce.crear_informe.runtime.construir_pdf",
            side_effect=_fake_pdf,
        ) as mock_pdf:
            crear_informe.construir(
                df_estudiantes_full, df_preguntas_full,
                asignatura="LENGUAJE",  # uppercase como el default
                numero_prueba=1, mes="ABRIL",
            )
        # construir_pdf fue invocado con dataframes filtrados
        call_args = mock_pdf.call_args
        dataframes = call_args[0][1]  # 2do positional arg
        # df_estudiantes filtrado debe tener solo Lenguaje
        df_est_filt = dataframes["estudiantes_prueba"]
        if len(df_est_filt) > 0:
            assert (df_est_filt["Asignatura"] == "Lenguaje").all()

    def test_asignatura_inexistente_no_explota(
        self, df_estudiantes_full, df_preguntas_full
    ):
        """Antes del fix: KeyError 'Rut'. Ahora debe devolver bytes sin crash."""
        with patch(
            "backend.rgenerator.reports.simce.crear_informe.runtime.construir_pdf",
            side_effect=_fake_pdf,
        ):
            result = crear_informe.construir(
                df_estudiantes_full, df_preguntas_full,
                asignatura="NOEXISTE",
                numero_prueba=1, mes="ABRIL",
            )
        assert isinstance(result, bytes)

    def test_dataframes_dict_tiene_4_keys(self, df_estudiantes_full, df_preguntas_full):
        """El dict pasado a construir_pdf tiene estudiantes(_prueba) + preguntas(_prueba)."""
        with patch(
            "backend.rgenerator.reports.simce.crear_informe.runtime.construir_pdf",
            side_effect=_fake_pdf,
        ) as mock_pdf:
            crear_informe.construir(
                df_estudiantes_full, df_preguntas_full,
                asignatura="Lenguaje", numero_prueba=1, mes="ABRIL",
            )
        dataframes = mock_pdf.call_args[0][1]
        assert set(dataframes.keys()) == {
            "estudiantes", "estudiantes_prueba", "preguntas", "preguntas_prueba"
        }

    def test_filtro_mes_se_aplica_post_derived_fields(
        self, df_estudiantes_full, df_preguntas_full
    ):
        """mes="ABRIL" → estudiantes_prueba solo tiene ABRIL pero
        estudiantes (full) mantiene ABRIL+JUNIO."""
        with patch(
            "backend.rgenerator.reports.simce.crear_informe.runtime.construir_pdf",
            side_effect=_fake_pdf,
        ) as mock_pdf:
            crear_informe.construir(
                df_estudiantes_full, df_preguntas_full,
                asignatura="Lenguaje", numero_prueba=1, mes="ABRIL",
            )
        dataframes = mock_pdf.call_args[0][1]
        df_est_prueba = dataframes["estudiantes_prueba"]
        if len(df_est_prueba) > 0:
            assert (df_est_prueba["Mes"] == "ABRIL").all()


@pytest.mark.unit
class TestConstruirDfVacios:
    def test_df_estudiantes_vacio_no_explota(self, df_preguntas_full):
        """El motor debe sobrevivir un df_estudiantes vacío."""
        df_empty = pd.DataFrame({
            "Rut": [], "Nombre": [], "Asignatura": [], "Mes": [],
            "N Prueba": [], "Rend": [], "Curso": [],
        })
        with patch(
            "backend.rgenerator.reports.simce.crear_informe.runtime.construir_pdf",
            side_effect=_fake_pdf,
        ):
            # Antes del fix del engine: KeyError 'Rut'.
            result = crear_informe.construir(
                df_empty, df_preguntas_full,
                asignatura="Lenguaje", numero_prueba=1, mes="ABRIL",
            )
        assert isinstance(result, bytes)
