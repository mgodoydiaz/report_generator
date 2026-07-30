"""Tests del detector/validador de la dimensión asignatura.

`reports/asignatura.py` es la fuente única de tres decisiones que hoy
consumen `report-options`, `export-pdf` y `dispatch_v2`:

    1. cuál columna es la asignatura,
    2. si hay que pedirle al usuario que elija una (≥2 valores),
    3. si los filtros efectivos la fijan a exactamente una.

Un bug acá deja pasar informes que mezclan LECTURA y MATEMATICA (cada
alumno contado dos veces) o bloquea indicadores de una sola asignatura.
"""
from __future__ import annotations

import pandas as pd
import pytest

from backend.rgenerator.reports import asignatura as asignaturas
from backend.rgenerator.reports.errores import (
    AsignaturaRequerida,
    DatosInsuficientes,
)


@pytest.mark.unit
class TestNombreDeDimension:
    @pytest.mark.parametrize("nombre", [
        "Asignatura",
        "asignatura",
        "ASIGNATURA",
        "Asignatúra",          # con tilde (dato sucio del Excel)
        "ASIGNATURÁ",
        "asignatura_evaluada",
        "Asignatura Evaluada",
        "  Asignatura  ",
    ])
    def test_reconoce_variantes(self, nombre):
        assert asignaturas.es_nombre_asignatura(nombre) is True

    @pytest.mark.parametrize("nombre", [
        "Curso", "Año", "Mes", "Nivel", "Hito", "", None, "Signatura",
    ])
    def test_descarta_lo_que_no_es(self, nombre):
        assert asignaturas.es_nombre_asignatura(nombre) is False

    def test_normalizar_saca_tildes_y_baja_a_minusculas(self):
        assert asignaturas.normalizar("Asignatúra  EVALUADA") == "asignatura evaluada"


@pytest.mark.unit
class TestDeteccionEnDataFrames:
    def test_dos_asignaturas_en_un_dataframe(self):
        df = pd.DataFrame({"Asignatura": ["LECTURA", "MATEMATICA", "LECTURA"]})
        assert asignaturas.dimension_asignatura(df) == (
            "Asignatura", ["LECTURA", "MATEMATICA"]
        )

    def test_una_sola_asignatura(self):
        df = pd.DataFrame({"Asignatura": ["LENGUAJE", "LENGUAJE"]})
        columna, valores = asignaturas.dimension_asignatura(df)
        assert (columna, valores) == ("Asignatura", ["LENGUAJE"])
        assert asignaturas.requiere_seleccion(valores) is False

    def test_columna_ausente(self):
        df = pd.DataFrame({"Curso": ["II A"], "Mes": ["ABRIL"]})
        assert asignaturas.dimension_asignatura(df) == (None, [])

    def test_ignora_nulos_y_vacios(self):
        df = pd.DataFrame({"Asignatura": ["LECTURA", None, "", "  ", "LECTURA"]})
        assert asignaturas.dimension_asignatura(df) == ("Asignatura", ["LECTURA"])

    def test_dedup_case_insensitive(self):
        df = pd.DataFrame({"Asignatura": ["Lectura", "LECTURA", "lectura"]})
        _, valores = asignaturas.dimension_asignatura(df)
        assert len(valores) == 1

    def test_acumula_valores_de_todos_los_roles(self):
        dataframes = {
            "estudiantes": pd.DataFrame({"Asignatura": ["LECTURA"]}),
            "preguntas": pd.DataFrame({"Asignatura": ["MATEMATICA"]}),
        }
        assert asignaturas.dimension_asignatura(dataframes) == (
            "Asignatura", ["LECTURA", "MATEMATICA"]
        )

    def test_dict_de_dataframes_sin_la_columna(self):
        dataframes = {"estudiantes": pd.DataFrame({"Curso": ["II A"]})}
        assert asignaturas.dimension_asignatura(dataframes) == (None, [])

    def test_dict_vacio_y_none(self):
        assert asignaturas.dimension_asignatura({}) == (None, [])
        assert asignaturas.dimension_asignatura(None) == (None, [])


@pytest.mark.unit
class TestDeteccionEnCatalogos:
    def test_formato_dimensiones_filtrables(self):
        dims = [
            {"id_dimension": 1, "name": "Curso", "values": ["II A"]},
            {"id_dimension": 2, "name": "Asignatura", "values": ["MATEMATICA", "lectura"]},
        ]
        assert asignaturas.dimension_asignatura(dims) == (
            "Asignatura", ["lectura", "MATEMATICA"]
        )

    def test_lista_de_nombres_sin_valores(self):
        assert asignaturas.dimension_asignatura(["Curso", "Asignatura"]) == (
            "Asignatura", []
        )

    def test_dict_nombre_a_valores(self):
        fuente = {"Curso": ["II A"], "Asignatura": ["LECTURA", "MATEMATICA"]}
        assert asignaturas.dimension_asignatura(fuente) == (
            "Asignatura", ["LECTURA", "MATEMATICA"]
        )


@pytest.mark.unit
class TestDescriptor:
    def test_dos_valores_emite_el_campo(self):
        df = pd.DataFrame({"Asignatura": ["LECTURA", "MATEMATICA"]})
        assert asignaturas.descriptor(df) == {
            "requerida": True,
            "dimension": "Asignatura",
            "valores": ["LECTURA", "MATEMATICA"],
        }

    def test_un_valor_no_emite_nada(self):
        assert asignaturas.descriptor(pd.DataFrame({"Asignatura": ["LECTURA"]})) is None

    def test_sin_columna_no_emite_nada(self):
        assert asignaturas.descriptor(pd.DataFrame({"Curso": ["II A"]})) is None

    def test_columna_presente_pero_toda_vacia(self):
        df = pd.DataFrame({"Asignatura": [None, ""]})
        assert asignaturas.descriptor(df) is None


@pytest.mark.unit
class TestFiltrosEfectivos:
    def test_lee_por_nombre_de_columna(self):
        filtros = {"Asignatura": ["LECTURA"], "Curso": "II A"}
        assert asignaturas.valores_en_filtros(filtros) == ["LECTURA"]

    def test_lee_por_id_de_dimension(self):
        filtros = {"7": ["MATEMATICA"], "3": "II A"}
        assert asignaturas.valores_en_filtros(filtros, claves={"7"}) == ["MATEMATICA"]

    def test_escalar_y_lista(self):
        assert asignaturas.valores_en_filtros({"Asignatura": "LECTURA"}) == ["LECTURA"]
        assert asignaturas.valores_en_filtros(
            {"Asignatura": ["LECTURA", "MATEMATICA"]}
        ) == ["LECTURA", "MATEMATICA"]

    def test_sin_mencion_devuelve_vacio(self):
        assert asignaturas.valores_en_filtros({"Curso": "II A"}, claves={"7"}) == []
        assert asignaturas.valores_en_filtros(None) == []

    def test_partir_filtros_saca_la_asignatura_del_resto(self):
        resto, elegidas = asignaturas.partir_filtros(
            {"Curso": "II A", "Asignatura": ["LECTURA"]}
        )
        assert resto == {"Curso": "II A"}
        assert elegidas == ["LECTURA"]


@pytest.mark.unit
class TestResolverSeleccion:
    def test_una_sola_en_datos_se_usa_esa(self):
        """Sin filtro y con 1 asignatura NO se inventa el literal LENGUAJE."""
        assert asignaturas.resolver_seleccion(["MATEMATICA"], []) == "MATEMATICA"

    def test_sin_asignaturas_devuelve_none(self):
        assert asignaturas.resolver_seleccion([], []) is None

    def test_dos_en_datos_con_una_elegida(self):
        elegida = asignaturas.resolver_seleccion(
            ["LECTURA", "MATEMATICA"], ["LECTURA"]
        )
        assert elegida == "LECTURA"

    def test_dos_en_datos_sin_elegir_falla(self):
        with pytest.raises(AsignaturaRequerida) as exc:
            asignaturas.resolver_seleccion(["LECTURA", "MATEMATICA"], [])
        detalle = str(exc.value)
        assert "varias asignaturas" in detalle
        assert "LECTURA" in detalle and "MATEMATICA" in detalle

    def test_dos_en_datos_eligiendo_dos_falla(self):
        with pytest.raises(AsignaturaRequerida) as exc:
            asignaturas.resolver_seleccion(
                ["LECTURA", "MATEMATICA"], ["LECTURA", "MATEMATICA"]
            )
        assert "UNA sola asignatura" in str(exc.value)

    def test_es_un_datos_insuficientes(self):
        """El router ya traduce DatosInsuficientes a 400: hereda de ahí."""
        assert issubclass(AsignaturaRequerida, DatosInsuficientes)


@pytest.mark.unit
class TestFiltrarDataframes:
    def test_recorta_todos_los_roles(self):
        dataframes = {
            "estudiantes": pd.DataFrame({
                "Asignatura": ["LECTURA", "MATEMATICA"], "Logro": [1, 2],
            }),
            "preguntas": pd.DataFrame({
                "Asignatura": ["LECTURA", "LECTURA"], "Logro": [3, 4],
            }),
        }
        out = asignaturas.filtrar_dataframes(dataframes, "Asignatura", "LECTURA")
        assert len(out["estudiantes"]) == 1
        assert len(out["preguntas"]) == 2

    def test_case_insensitive(self):
        dataframes = {"estudiantes": pd.DataFrame({"Asignatura": ["Lectura"]})}
        out = asignaturas.filtrar_dataframes(dataframes, "Asignatura", "LECTURA")
        assert len(out["estudiantes"]) == 1

    def test_rol_sin_filas_se_omite(self):
        """Mismo contrato que `data.py`: una metric sin records no aparece."""
        dataframes = {
            "estudiantes": pd.DataFrame({"Asignatura": ["LECTURA"]}),
            "preguntas": pd.DataFrame({"Asignatura": ["MATEMATICA"]}),
        }
        out = asignaturas.filtrar_dataframes(dataframes, "Asignatura", "LECTURA")
        assert set(out) == {"estudiantes"}

    def test_rol_sin_la_columna_pasa_intacto(self):
        dataframes = {"otros": pd.DataFrame({"Curso": ["II A", "II B"]})}
        out = asignaturas.filtrar_dataframes(dataframes, "Asignatura", "LECTURA")
        assert len(out["otros"]) == 2

    def test_sin_asignatura_no_toca_nada(self):
        dataframes = {"estudiantes": pd.DataFrame({"Asignatura": ["A", "B"]})}
        out = asignaturas.filtrar_dataframes(dataframes, "Asignatura", None)
        assert len(out["estudiantes"]) == 2
