"""Tests del loader DB → DataFrame del motor PDF v2.

`cargar_dataframes_indicator` en `backend/rgenerator/reports/data.py` es
una pieza crítica donde el bug del 2026-05-19 (case "Rut" vs "RUT") tuvo
origen. Esta suite cubre los helpers de naming + el flow completo.
"""
from __future__ import annotations

import pytest

from backend.rgenerator.reports.data import (
    _humanize_column,
    _to_field_name,
    cargar_dataframes_indicator,
)
from tests.factories import (
    make_dimension, make_indicator, make_metric, make_metric_data, make_org,
)


# ─────────────────────────────────────────────────────────────────────────
# Unit tests de los helpers de naming
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestToFieldName:
    @pytest.mark.parametrize("inp,expected", [
        ("RUT", "_rut"),
        ("Rut", "_rut"),
        ("rut", "_rut"),
        ("Año", "_ano"),  # NFKD remueve tilde
        ("Eje Temático", "_eje_tematico"),
        ("N Prueba", "_n_prueba"),
        ("  Curso  ", "_curso"),  # strip
        ("N° Pregunta", "_n_pregunta"),
        ("UPPER CASE", "_upper_case"),
    ])
    def test_normalizacion(self, inp, expected):
        assert _to_field_name(inp) == expected


@pytest.mark.unit
class TestHumanizeColumn:
    @pytest.mark.parametrize("inp,expected", [
        ("_rut", "Rut"),
        ("_ano", "Año"),
        ("_eje_tematico", "Eje Temático"),
        ("_curso", "Curso"),
        ("_logro", "Logro"),
        ("_porclogro", "PorcLogro"),  # SIMCE Panguipulli override
        ("_n_pregunta", "N° Pregunta"),  # override
        # Dimensión producida por normalize_name en el pipeline DIA: debe
        # conservar el guion bajo (el esquema DIA la usa como entity_field
        # "Nombre_Norm"). Sin override quedaría "Nombre Norm" (con espacio) y
        # las derived_fields Avance/Mejora_vs_Inicio fallarían con KeyError.
        ("_nombre_norm", "Nombre_Norm"),
    ])
    def test_humanize_con_y_sin_override(self, inp, expected):
        assert _humanize_column(inp) == expected


# ─────────────────────────────────────────────────────────────────────────
# Integration: cargar_dataframes_indicator
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture
def indicador_con_datos(db_session, org):
    """Setup mínimo para cargar_dataframes_indicator: indicator + 1 metric
    de cada rol (estudiantes + preguntas + otro)."""
    dim_curso = make_dimension(db_session, org, name="Curso")
    dim_rut = make_dimension(db_session, org, name="RUT")
    dim_asig = make_dimension(db_session, org, name="Asignatura")

    m_est = make_metric(
        db_session, org,
        name="Resultados SIMCE por Estudiante",  # nombre → rol "estudiantes"
        data_type="object",
        fields=[{"name": "Rend", "type": "float"}],
        dimensions=[dim_curso, dim_rut, dim_asig],
    )
    m_preg = make_metric(
        db_session, org,
        name="Resultados SIMCE por Pregunta",
        data_type="object",
        fields=[{"name": "Logro", "type": "float"}],
        dimensions=[dim_curso, dim_asig],
    )
    ind = make_indicator(db_session, org, name="SIMCE", metrics=[m_est, m_preg])

    # 3 rows estudiantes: 2 Lenguaje + 1 Matemáticas
    for rut, rend, asig in [("1-1", 0.5, "Lenguaje"), ("1-2", 0.7, "Lenguaje"), ("2-1", 0.6, "Matemáticas")]:
        make_metric_data(
            db_session, m_est, value={"Rend": rend},
            dimensions_json={
                str(dim_curso.id_dimension): "II A",
                str(dim_rut.id_dimension): rut,
                str(dim_asig.id_dimension): asig,
            },
        )
    # 2 rows preguntas
    for asig, logro in [("Lenguaje", 0.6), ("Matemáticas", 0.8)]:
        make_metric_data(
            db_session, m_preg, value={"Logro": logro},
            dimensions_json={
                str(dim_curso.id_dimension): "II A",
                str(dim_asig.id_dimension): asig,
            },
        )
    return ind


@pytest.mark.integration
class TestCargarDataframesIndicator:
    def test_carga_basica_devuelve_estudiantes_y_preguntas(
        self, db_session, indicador_con_datos
    ):
        ind = indicador_con_datos
        dfs = cargar_dataframes_indicator(
            db_session, indicator_id=ind.id_indicator, org_id=ind.org_id,
        )
        assert "estudiantes" in dfs
        assert "preguntas" in dfs
        # 3 rows en estudiantes, 2 en preguntas
        assert len(dfs["estudiantes"]) == 3
        assert len(dfs["preguntas"]) == 2

    def test_columnas_humanizadas(self, db_session, indicador_con_datos):
        """RUT en BD → "Rut" en DataFrame (bug del 2026-05-19)."""
        ind = indicador_con_datos
        dfs = cargar_dataframes_indicator(
            db_session, indicator_id=ind.id_indicator, org_id=ind.org_id,
        )
        df_est = dfs["estudiantes"]
        assert "Rut" in df_est.columns, f"Cols: {list(df_est.columns)}"
        assert "Curso" in df_est.columns
        assert "Asignatura" in df_est.columns
        assert "Rend" in df_est.columns  # field del object value

    def test_filtros_estructurales(self, db_session, indicador_con_datos):
        """filtros={Asignatura: Lenguaje} debe dejar solo 2 estudiantes."""
        ind = indicador_con_datos
        dfs = cargar_dataframes_indicator(
            db_session, indicator_id=ind.id_indicator, org_id=ind.org_id,
            filtros={"Asignatura": "Lenguaje"},
        )
        assert len(dfs["estudiantes"]) == 2

    def test_indicator_inexistente_lanza_value_error(self, db_session):
        with pytest.raises(ValueError, match="no existe"):
            cargar_dataframes_indicator(db_session, indicator_id=99999, org_id=1)

    def test_indicator_de_otra_org_lanza_value_error(self, db_session, org):
        from tests.factories import make_org as _make_org
        other = _make_org(db_session)
        ind_other = make_indicator(db_session, other, name="Foreign")
        # Pasamos org_id=org.id pero indicator_id es de otra → no existe
        with pytest.raises(ValueError, match="no existe"):
            cargar_dataframes_indicator(
                db_session, indicator_id=ind_other.id_indicator, org_id=org.id,
            )
