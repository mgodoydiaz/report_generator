"""Tests del generador de informes Word (backend/rgenerator/reports/word/).

Cubre: registry por nombre, helpers del engine, render end-to-end (bytes
.docx válidos) y los endpoints /api/reports/word/*.
"""
from __future__ import annotations

import io
import zipfile

import pandas as pd
import pytest

from backend.rgenerator.reports import word as word_reports
from backend.rgenerator.reports.word.engine import tabla_desde_df
from tests.factories import (
    make_dimension, make_indicator, make_metric, make_metric_data,
)


# ─────────────────────────────────────────────────────────────────────────
# Unit: registry
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestRegistry:
    def test_descubre_resumen_indicador(self):
        registry = word_reports.get_registry(refresh=True)
        assert "resumen_indicador" in registry

    def test_obtener_modulo_desconocido_lanza_keyerror(self):
        with pytest.raises(KeyError, match="no registrado"):
            word_reports.obtener_modulo("no_existe_xyz")

    def test_listar_informes_incluye_metadata(self):
        informes = word_reports.listar_informes()
        por_nombre = {i["nombre"]: i for i in informes}
        assert "resumen_indicador" in por_nombre
        info = por_nombre["resumen_indicador"]
        assert info["label"]
        assert info["plantilla"] == "resumen_indicador.docx"
        assert info["plantilla_existe"] is True


# ─────────────────────────────────────────────────────────────────────────
# Unit: helpers del engine
# ─────────────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestTablaDesdeDf:
    def test_normaliza_claves_y_formatea(self):
        df = pd.DataFrame({
            "Categoría": ["II A", "II B"],
            "N": [10, 12],
            "Promedio": [0.853, 0.7],
        })
        filas = tabla_desde_df(df, formatos={"Promedio": ".1%"})
        assert filas[0] == {"categoria": "II A", "n": 10, "promedio": "85.3%"}

    def test_nan_se_convierte_en_string_vacio(self):
        df = pd.DataFrame({"A": [1.0, float("nan")]})
        filas = tabla_desde_df(df)
        assert filas[1]["a"] == ""

    def test_subset_de_columnas(self):
        df = pd.DataFrame({"A": [1], "B": [2], "C": [3]})
        filas = tabla_desde_df(df, columnas=["C", "A"])
        assert list(filas[0].keys()) == ["c", "a"]


# ─────────────────────────────────────────────────────────────────────────
# Unit: placeholders + render end-to-end (sin DB)
# ─────────────────────────────────────────────────────────────────────────

@pytest.fixture
def df_estudiantes_sintetico():
    return pd.DataFrame({
        "Curso": ["II A", "II A", "II B", "II B"],
        "Rend": [0.5, 0.7, 0.6, 0.8],
        "Estudiante": ["Ana", "Beto", "Cata", "Dani"],
    })


@pytest.mark.unit
class TestRenderInforme:
    def test_placeholders_de_la_plantilla(self):
        modulo = word_reports.obtener_modulo("resumen_indicador")
        placeholders = word_reports.listar_placeholders(modulo)
        for esperado in ("titulo", "fecha", "n_registros", "resumen", "grafico_logro"):
            assert esperado in placeholders, f"falta {esperado} en {placeholders}"

    def test_render_devuelve_docx_valido(self, df_estudiantes_sintetico):
        modulo = word_reports.obtener_modulo("resumen_indicador")
        docx_bytes = word_reports.render_informe(
            modulo,
            {"estudiantes": df_estudiantes_sintetico},
            params={"titulo": "Test Informe"},
        )
        # Un .docx es un zip: magic PK + contiene word/document.xml
        assert docx_bytes[:2] == b"PK"
        with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        assert "Test Informe" in xml
        # El loop de tabla se expandió: aparecen los cursos
        assert "II A" in xml and "II B" in xml
        # No quedaron códigos sin renderizar
        assert "{{" not in xml

    def test_render_sin_datos_lanza_valueerror(self):
        modulo = word_reports.obtener_modulo("resumen_indicador")
        with pytest.raises(ValueError, match="no tiene datos"):
            word_reports.render_informe(modulo, {"estudiantes": pd.DataFrame()})


# ─────────────────────────────────────────────────────────────────────────
# Integration: endpoints /api/reports/word/*
# ─────────────────────────────────────────────────────────────────────────

@pytest.fixture
def indicador_word(db_session, org):
    """Indicator mínimo con 1 metric de estudiantes y 4 rows."""
    dim_curso = make_dimension(db_session, org, name="Curso")
    m_est = make_metric(
        db_session, org,
        name="Resultados por Estudiante",
        data_type="object",
        fields=[{"name": "Rend", "type": "float"}],
        dimensions=[dim_curso],
    )
    ind = make_indicator(db_session, org, name="Word Test", metrics=[m_est])
    for curso, rend in [("II A", 0.5), ("II A", 0.7), ("II B", 0.6), ("II B", 0.8)]:
        make_metric_data(
            db_session, m_est, value={"Rend": rend},
            dimensions_json={str(dim_curso.id_dimension): curso},
        )
    return ind


@pytest.mark.integration
class TestEndpointsWord:
    def test_listar_informes(self, client_auth):
        res = client_auth.get("/api/reports/word/informes")
        assert res.status_code == 200
        nombres = [i["nombre"] for i in res.json()]
        assert "resumen_indicador" in nombres

    def test_placeholders_endpoint(self, client_auth):
        res = client_auth.get("/api/reports/word/informes/resumen_indicador/placeholders")
        assert res.status_code == 200
        assert "titulo" in res.json()["placeholders"]

    def test_placeholders_informe_desconocido_404(self, client_auth):
        res = client_auth.get("/api/reports/word/informes/nope/placeholders")
        assert res.status_code == 404

    def test_generar_word_ok(self, client_auth, indicador_word):
        res = client_auth.post(
            "/api/reports/word/resumen_indicador",
            json={"indicator_id": indicador_word.id_indicator,
                  "params": {"titulo": "Informe de Prueba"}},
        )
        assert res.status_code == 200, res.text
        assert res.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument"
        )
        assert res.content[:2] == b"PK"

    def test_generar_word_informe_desconocido_404(self, client_auth, indicador_word):
        res = client_auth.post(
            "/api/reports/word/no_existe",
            json={"indicator_id": indicador_word.id_indicator},
        )
        assert res.status_code == 404

    def test_generar_word_indicator_inexistente_400(self, client_auth):
        res = client_auth.post(
            "/api/reports/word/resumen_indicador",
            json={"indicator_id": 999999},
        )
        assert res.status_code == 400
