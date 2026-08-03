"""Guardia: cada `df_input` del esquema debe existir entre los dataframes que
`crear_informe.construir` publica, y el recorte a la prueba del informe debe
usarse donde corresponde.

QA 2026-08-03 (H-1): la sección "Logro Promedio por Habilidad" declaraba
`"df_input": "habilidad"` — el histórico del año filtrado solo por asignatura —
mientras las otras 6 secciones usaban el recorte a la prueba. Bajo un encabezado
que decía SEPTIEMBRE 2025 el único gráfico que le dice al profesor qué habilidad
reforzar mostraba el promedio abril-septiembre: hasta 10 pp de error e inversión
del ranking de habilidades.

El token correcto (`habilidad_prueba`) ya lo construía y publicaba
`crear_informe.py`; nadie lo consumía. Un `df_input` mal escrito no rompe nada
visible — la sección sale vacía o, peor, con los datos de otro período — así que
la guardia es genérica: se resuelve contra los dataframes REALES que arma
`construir`, no contra una lista hardcodeada que se desincronizaría.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from backend.rgenerator.reports.simce_panguipulli import crear_informe

ESQUEMA_PATH = (
    Path(crear_informe.__file__).parent / "esquema.json"
)

MESES = ["ABRIL", "MAYO", "AGOSTO", "SEPTIEMBRE"]
HABILIDADES = ["Localizar información", "Reflexionar sobre el texto"]
MES_INFORME = "SEPTIEMBRE"


@pytest.fixture(scope="module")
def esquema() -> dict:
    with open(ESQUEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def _df_inputs_declarados(esquema: dict) -> set[str]:
    """Todos los tokens de dataframe que el esquema referencia."""
    tokens: set[str] = set()
    for sec in esquema.get("secciones_fijas") or []:
        if sec.get("df_input"):
            tokens.add(sec["df_input"])
    dinamicas = esquema.get("secciones_dinamicas") or {}
    if dinamicas.get("df_iterar"):
        tokens.add(dinamicas["df_iterar"])
    for sec in dinamicas.get("secciones") or []:
        if sec.get("df_input"):
            tokens.add(sec["df_input"])
    return tokens


@pytest.fixture
def df_estudiantes() -> pd.DataFrame:
    filas = []
    for i, mes in enumerate(MESES, start=1):
        for rut, base in (("1-1", 0.30), ("2-2", 0.70)):
            filas.append({
                "Rut": rut,
                "Nombre": f"Alumno {rut}",
                "Curso": "II° medio E",
                "Asignatura": "LENGUAJE",
                "Mes": mes,
                "N Prueba": i,
                # Sube 5 pp por prueba: el promedio anual difiere del de
                # septiembre, que es justo lo que la guardia necesita distinguir.
                "PorcLogro": base + 0.05 * (i - 1),
            })
    return pd.DataFrame(filas)


@pytest.fixture
def df_habilidad() -> pd.DataFrame:
    filas = []
    for i, mes in enumerate(MESES, start=1):
        for j, habilidad in enumerate(HABILIDADES):
            filas.append({
                "Curso": "II° medio E",
                "Asignatura": "LENGUAJE",
                "Mes": mes,
                "N Prueba": i,
                "Habilidad": habilidad,
                "LogroHabilidad": 0.30 + 0.10 * (i - 1) + 0.05 * j,
            })
    return pd.DataFrame(filas)


@pytest.fixture
def dataframes_publicados(monkeypatch, df_estudiantes, df_habilidad) -> dict:
    """Los `dataframes` que `construir` le pasa a `runtime.construir_pdf`.

    Se intercepta el orquestador en vez de generar el PDF: la guardia es sobre
    el contrato esquema↔constructor, y WeasyPrint no está garantizado en el
    entorno de tests.
    """
    capturado: dict = {}

    def _fake_construir_pdf(tipo, dataframes, **kwargs):
        capturado.update(dataframes)
        return b"%PDF-1.4 fake\n"

    monkeypatch.setattr(crear_informe.runtime, "construir_pdf", _fake_construir_pdf)
    salida = crear_informe.construir(
        df_estudiantes,
        df_habilidad,
        asignatura="LENGUAJE",
        numero_prueba=len(MESES),
        mes=MES_INFORME,
    )
    assert salida.startswith(b"%PDF")
    assert capturado, "construir() no llegó a llamar a runtime.construir_pdf"
    return capturado


@pytest.mark.unit
class TestEsquemaPanguipulliDfInput:
    def test_toda_seccion_referencia_un_df_publicado(self, esquema, dataframes_publicados):
        declarados = _df_inputs_declarados(esquema)
        assert declarados, "el esquema no declara ningún df_input — ¿cambió el formato?"
        huerfanos = declarados - set(dataframes_publicados)
        assert not huerfanos, (
            f"df_input sin dataframe correspondiente: {sorted(huerfanos)}. "
            f"Publicados por crear_informe.py: {sorted(dataframes_publicados)}"
        )

    def test_la_seccion_de_habilidad_usa_el_recorte_a_la_prueba(self, esquema):
        """El fix de H-1, fijado como contrato.

        El promedio anual sigue disponible en `habilidad`: si alguna vez se
        quiere mostrar, va como una SEGUNDA sección con el título diciéndolo.
        """
        secciones = [s for s in esquema["secciones_fijas"]
                     if s.get("titulo") == "Logro Promedio por Habilidad"]
        assert len(secciones) == 1
        assert secciones[0]["df_input"] == "habilidad_prueba"

    def test_habilidad_prueba_solo_trae_el_mes_del_informe(self, dataframes_publicados):
        df = dataframes_publicados["habilidad_prueba"]
        assert set(df["Mes"].astype(str)) == {MES_INFORME}
        assert len(df) == len(HABILIDADES)

    def test_habilidad_conserva_el_historico_completo(self, dataframes_publicados):
        """El df anual sigue publicado: el fix recorta el consumo, no el dato."""
        df = dataframes_publicados["habilidad"]
        assert set(df["Mes"].astype(str)) == set(MESES)

    def test_el_recorte_cambia_el_valor_graficado(self, dataframes_publicados):
        """Sin esto la guardia pasaría aunque ambos df dieran lo mismo."""
        anual = dataframes_publicados["habilidad"]["LogroHabilidad"].mean()
        prueba = dataframes_publicados["habilidad_prueba"]["LogroHabilidad"].mean()
        assert prueba != pytest.approx(anual)

    def test_las_columnas_que_la_seccion_espera_estan_en_el_df(self, esquema,
                                                               dataframes_publicados):
        seccion = next(s for s in esquema["secciones_fijas"]
                       if s.get("titulo") == "Logro Promedio por Habilidad")
        params = seccion["params"]
        df = dataframes_publicados[seccion["df_input"]]
        for clave in ("columna_valor", "agrupar_principal_por", "agrupar_secundario_por"):
            columna = params[clave]
            assert columna in df.columns, (
                f"la sección pide '{columna}' ({clave}) y "
                f"'{seccion['df_input']}' no la tiene: {list(df.columns)}"
            )
