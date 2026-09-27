# -*- coding: utf-8 -*-
"""Regresión de la regla de canonización de Establecimiento del pipeline DIA
(id 21, prod), definida en `scripts/dia_normalizar_pipeline_21.py::TRANSFORMACION`
y aplicada por el `ModifyColumnValues` real
(`backend.rgenerator.tooling.etl_tools.modificar_valores_columna`).

Contexto (QA 2026-09-26, ver `docs/.../06_regla_establecimiento.md` en el
diagnóstico de la carga DIA de sept-2026): el Colegio Básico y el Liceo de
Panguipulli comparten RBD y el mismo texto largo en B5/portada PDF, así que
la regla los separa por curso (1°-6° básico → 'Colegio Básico'; 7°, 8° y
media → 'Liceo PHP Panguipulli'). Pullinque no tiene ese problema (RBD y
nombre propios) y siempre cae en 'Liceo PHP Pullinque'.

Esta suite tiene tres partes:
  1. `_TRANSFORMACION_V1_HISTORICA` — snapshot literal de la regla que estuvo
     en prod hasta este sprint (corte por `curso[:1] in {'1'..'6'}`, sin
     manejo de NaN/idempotencia). Documenta los bugs que motivaron la v2,
     para que no se vuelvan a introducir por accidente si alguien "simplifica"
     la regex de nuevo.
  2. Casos reales de prod (formatos de curso vistos en los archivos de
     BÁSICA/PANGUIPULLI/PULLINQUE) contra la regla VIGENTE
     (`TRANSFORMACION`, importada del script — no una copia).
  3. Casos sintéticos / límite contra la regla vigente: variantes de
     ortografía de curso y establecimiento, nulos, idempotencia.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from dia_normalizar_pipeline_21 import (  # noqa: E402
    MARCA,
    START_MARKER,
    TRANSFORMACION,
    paso_canonico,
    transformar,
    verificar,
)
from backend.rgenerator.tooling.etl_tools import modificar_valores_columna  # noqa: E402

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────

def _aplicar(transformacion: dict, establecimiento, curso):
    """Corre el `ModifyColumnValues` real sobre una fila sintética."""
    df = pd.DataFrame({"Establecimiento": [establecimiento], "Curso": [curso]})
    df = modificar_valores_columna(df, [copy.deepcopy(transformacion)])
    return df["Establecimiento"].iloc[0]


# Snapshot de la regla que estuvo en prod hasta este sprint (2026-09-26).
# NO importar esto de git history: se copia literal para que el test
# documente el bug con independencia de refactors futuros del script.
_ES_BASICA_V1 = "str(row['Curso']).strip()[:1] in ('1', '2', '3', '4', '5', '6')"
_TRANSFORMACION_V1_HISTORICA = {
    "columna": "Establecimiento",
    "operacion": "math",
    "usa_fila": True,
    "valores": [
        {"condicion": "'PULLINQUE' in str(row['Establecimiento']).upper()",
         "expresion": "'Liceo PHP Pullinque'"},
        {"condicion": f"'PANGUIPULLI' in str(row['Establecimiento']).upper() and {_ES_BASICA_V1}",
         "expresion": "'Colegio Básico'"},
        {"condicion": "'PANGUIPULLI' in str(row['Establecimiento']).upper()",
         "expresion": "'Liceo PHP Panguipulli'"},
        {"condicion": "*",
         "expresion": "str(row['Establecimiento'])"},
    ],
}

NOMBRE_LARGO_PANGUIPULLI = "LICEO TECNICO PROFESIONAL PEOPLE HELP PEOPLE DE PANGUIPULLI"
NOMBRE_LARGO_PULLINQUE = "LICEO TECNICO PROFESIONAL PEOPLE HELP PEOPLE PULLINQUE"


# ─────────────────────────────────────────────────────────────────────────
# 1) Bugs de la v1 (documentados como regresión — NO deben reaparecer)
# ─────────────────────────────────────────────────────────────────────────

class TestBugsV1Historica:
    """Cada caso reproduce un bug real de la regla que estuvo en prod.

    Se corre contra el snapshot v1, no contra `TRANSFORMACION` (que ya trae
    la v2), para dejar registro de por qué existe la v2.
    """

    def test_v1_no_reconocia_curso_con_cero_a_la_izquierda(self):
        # "01 A" (1° básico con cero a la izquierda) -> primer char "0",
        # fuera de {'1'..'6'} -> se iba (mal) al Liceo.
        r = _aplicar(_TRANSFORMACION_V1_HISTORICA, NOMBRE_LARGO_PANGUIPULLI, "01 A")
        assert r == "Liceo PHP Panguipulli"  # bug: debería ser Colegio Básico

    def test_v1_confundia_1_medio_con_1_basico(self):
        # "1 Medio A" / "1° Medio A": el primer char es "1", igual que 1°
        # básico -> la v1 los mandaba (mal) a Colegio Básico.
        for curso in ("1 Medio A", "1° Medio A"):
            r = _aplicar(_TRANSFORMACION_V1_HISTORICA, NOMBRE_LARGO_PANGUIPULLI, curso)
            assert r == "Colegio Básico"  # bug: es media, debería ser el Liceo

    def test_v1_no_era_idempotente_sobre_liceo_ya_canonico(self):
        # Re-aplicar la v1 sobre un valor YA canónico ('Liceo PHP
        # Panguipulli') con un curso de básica lo degradaba a 'Colegio
        # Básico' -- corromper data ya correcta si el pipeline corre 2 veces
        # sobre una fila que quedó con Curso de básica por error de origen.
        r = _aplicar(_TRANSFORMACION_V1_HISTORICA, "Liceo PHP Panguipulli", "1 A")
        assert r == "Colegio Básico"  # bug: no debería tocar un valor canónico

    def test_v1_convertia_nan_en_el_string_literal_nan(self):
        r = _aplicar(_TRANSFORMACION_V1_HISTORICA, np.nan, "1 A")
        assert r == "nan"  # bug: NaN se transformaba en el string "nan"

    def test_v1_convertia_none_en_el_string_literal_none(self):
        r = _aplicar(_TRANSFORMACION_V1_HISTORICA, None, "1 A")
        assert r == "None"  # bug: None se transformaba en el string "None"


# ─────────────────────────────────────────────────────────────────────────
# 2) Casos reales de prod (formatos de curso vistos en los archivos del
#    lote de sept-2026 — ver inventario en
#    diagnostico/regla_establecimiento_inventario.csv) contra la regla VIGENTE
# ─────────────────────────────────────────────────────────────────────────

CASOS_REALES = [
    # (establecimiento_crudo, curso_crudo, esperado)
    (NOMBRE_LARGO_PANGUIPULLI, "1 A", "Colegio Básico"),
    (NOMBRE_LARGO_PANGUIPULLI, "2 A", "Colegio Básico"),
    (NOMBRE_LARGO_PANGUIPULLI, "3 A", "Colegio Básico"),
    (NOMBRE_LARGO_PANGUIPULLI, "4 A", "Colegio Básico"),
    (NOMBRE_LARGO_PANGUIPULLI, "5 A", "Colegio Básico"),
    (NOMBRE_LARGO_PANGUIPULLI, "6 A", "Colegio Básico"),
    (NOMBRE_LARGO_PANGUIPULLI, "7 A", "Liceo PHP Panguipulli"),
    (NOMBRE_LARGO_PANGUIPULLI, "8 A", "Liceo PHP Panguipulli"),
    (NOMBRE_LARGO_PANGUIPULLI, "I A (TPT-610)", "Liceo PHP Panguipulli"),
    (NOMBRE_LARGO_PANGUIPULLI, "II B (TPI-510)", "Liceo PHP Panguipulli"),
    (NOMBRE_LARGO_PANGUIPULLI, "I A (TPI-510)", "Liceo PHP Panguipulli"),
    (NOMBRE_LARGO_PANGUIPULLI, "II B (TPA-710)", "Liceo PHP Panguipulli"),
    (NOMBRE_LARGO_PULLINQUE, "1 A", "Liceo PHP Pullinque"),
    (NOMBRE_LARGO_PULLINQUE, "II C (TPA-710)", "Liceo PHP Pullinque"),
]


@pytest.mark.parametrize("establecimiento,curso,esperado", CASOS_REALES)
def test_casos_reales_de_prod(establecimiento, curso, esperado):
    assert _aplicar(TRANSFORMACION, establecimiento, curso) == esperado


# ─────────────────────────────────────────────────────────────────────────
# 3) Casos sintéticos / límite contra la regla vigente (v2)
# ─────────────────────────────────────────────────────────────────────────

class TestReglaVigenteBasicaVsMedio:
    """La v2 exige dígito 1-6 anclado al inicio + separador, y excluye
    'MEDIO' explícito. Corrige los bugs de v1 documentados arriba."""

    @pytest.mark.parametrize("curso", [
        "1 A", "1° A", "1°A", "1ºA", "01 A", "6 B",
        "1° Básico A",  # básica deletreada PERO con el dígito presente: sí matchea
    ])
    def test_basica_1_a_6_con_digito_anclado(self, curso):
        assert _aplicar(TRANSFORMACION, NOMBRE_LARGO_PANGUIPULLI, curso) == "Colegio Básico"

    @pytest.mark.parametrize("curso", [
        "7 A", "7° A", "8° básico B",
        "I A (TPT-610)", "I° Medio A", "III A", "IV B (TPT-610)",
        "1 Medio A", "1° Medio A",  # el bug puntual que motivó la v2
    ])
    def test_media_y_7_8_basico_van_al_liceo(self, curso):
        assert _aplicar(TRANSFORMACION, NOMBRE_LARGO_PANGUIPULLI, curso) == "Liceo PHP Panguipulli"

    def test_1ro_a_con_digito_anclado_va_a_basica(self):
        # "1ro A": empieza con "1" + "r" (letra) -> matchea el separador
        # [ °ºA-Z] -> básica. Coherente con la regla (dígito al inicio).
        assert _aplicar(TRANSFORMACION, NOMBRE_LARGO_PANGUIPULLI, "1ro A") == "Colegio Básico"

    @pytest.mark.xfail(
        reason="Limitación conocida y documentada: cursos deletreados sin dígito "
               "('Primero Básico A') no matchean la regex ancorada a dígito. "
               "Requeriría un diccionario de ordinales en palabras, fuera del "
               "alcance de este fix (ver 06_regla_establecimiento.md).",
        strict=True,
    )
    def test_curso_deletreado_sin_digito_no_se_reconoce_como_basica(self):
        assert _aplicar(TRANSFORMACION, NOMBRE_LARGO_PANGUIPULLI, "Primero Básico A") == "Colegio Básico"

    @pytest.mark.xfail(
        reason="Limitación conocida: '1M A' es ambiguo entre \"1° Medio, sección A\" "
               "y \"1° básico, sección M\" -- no se puede desambiguar sin más contexto "
               "(no aparece en los datos reales de prod). Documentado en "
               "06_regla_establecimiento.md como riesgo abierto.",
        strict=True,
    )
    def test_abreviatura_1M_ambigua_no_se_resuelve(self):
        assert _aplicar(TRANSFORMACION, NOMBRE_LARGO_PANGUIPULLI, "1M A") == "Liceo PHP Panguipulli"


class TestReglaVigenteEstablecimientos:
    @pytest.mark.parametrize("establecimiento", [
        NOMBRE_LARGO_PANGUIPULLI,
        NOMBRE_LARGO_PANGUIPULLI.lower(),
        "LICEO TÉCNICO PROFESIONAL PEOPLE HELP PEOPLE DE PANGUIPULLI",  # con tilde
        "PANGUIPULLI",  # a secas
    ])
    def test_variantes_panguipulli_van_a_basica_o_liceo_segun_curso(self, establecimiento):
        assert _aplicar(TRANSFORMACION, establecimiento, "1 A") == "Colegio Básico"
        assert _aplicar(TRANSFORMACION, establecimiento, "I A (TPT-610)") == "Liceo PHP Panguipulli"

    def test_pullinque_a_secas_sin_split_por_curso(self):
        assert _aplicar(TRANSFORMACION, "Pullinque", "1 A") == "Liceo PHP Pullinque"
        assert _aplicar(TRANSFORMACION, "Pullinque", "IV B (TPT-610)") == "Liceo PHP Pullinque"

    def test_colegio_ajeno_no_se_toca(self):
        assert _aplicar(TRANSFORMACION, "ESCUELA X", "1 A") == "ESCUELA X"
        assert _aplicar(TRANSFORMACION, "ESCUELA X", "") == "ESCUELA X"

    def test_valores_ya_canonicos_se_mantienen_sin_reevaluar_curso(self):
        # Antes (v1) esto degradaba 'Liceo PHP Panguipulli' a 'Colegio
        # Básico' si el curso era de básica. Ahora un valor ya canónico se
        # deja intacto, sin importar el curso.
        assert _aplicar(TRANSFORMACION, "Liceo PHP Panguipulli", "1 A") == "Liceo PHP Panguipulli"
        assert _aplicar(TRANSFORMACION, "Colegio Básico", "I A (TPT-610)") == "Colegio Básico"
        assert _aplicar(TRANSFORMACION, "Liceo PHP Pullinque", "1 A") == "Liceo PHP Pullinque"

    def test_establecimiento_vacio_se_mantiene_vacio(self):
        assert _aplicar(TRANSFORMACION, "", "1 A") == ""

    def test_nan_se_preserva_como_nan_no_como_string(self):
        r = _aplicar(TRANSFORMACION, np.nan, "1 A")
        assert isinstance(r, float) and np.isnan(r)

    def test_none_se_preserva_como_none_no_como_string(self):
        assert _aplicar(TRANSFORMACION, None, "1 A") is None


class TestReglaVigenteCursoNuloOAtipico:
    """Cursos vacíos/nulos o fuera del vocabulario conocido (Kinder, NT1,
    PK) no tienen regla explícita: quedan en el Liceo por default (no
    matchean la regex de básica). Se documenta el comportamiento, no se
    exige que sea 'correcto' porque no está definido para esos casos."""

    @pytest.mark.parametrize("curso", ["Kinder A", "NT1", "PK A", "", np.nan, None])
    def test_cursos_fuera_de_vocabulario_van_al_liceo_por_default(self, curso):
        assert _aplicar(TRANSFORMACION, NOMBRE_LARGO_PANGUIPULLI, curso) == "Liceo PHP Panguipulli"


class TestIdempotencia:
    """Aplicar la regla dos veces no debe cambiar el resultado de la
    primera pasada — requisito explícito del pipeline (los tres cambios de
    dia_normalizar_pipeline_21.py se describen como idempotentes)."""

    @pytest.mark.parametrize("establecimiento,curso", [
        (NOMBRE_LARGO_PANGUIPULLI, "1 A"),
        (NOMBRE_LARGO_PANGUIPULLI, "01 A"),
        (NOMBRE_LARGO_PANGUIPULLI, "7 A"),
        (NOMBRE_LARGO_PANGUIPULLI, "I A (TPT-610)"),
        (NOMBRE_LARGO_PANGUIPULLI, "1 Medio A"),
        (NOMBRE_LARGO_PULLINQUE, "II C (TPA-710)"),
        ("ESCUELA X", "1 A"),
        ("", "1 A"),
        (np.nan, "1 A"),
        (None, "1 A"),
    ])
    def test_doble_aplicacion_no_cambia_el_resultado(self, establecimiento, curso):
        primera = _aplicar(TRANSFORMACION, establecimiento, curso)
        # segunda pasada: el establecimiento de entrada es el resultado de
        # la primera (simula correr el pipeline dos veces sobre la misma fila)
        segunda_input = primera
        segunda = _aplicar(TRANSFORMACION, segunda_input, curso)
        if isinstance(primera, float) and np.isnan(primera):
            assert isinstance(segunda, float) and np.isnan(segunda)
        else:
            assert segunda == primera


# ─────────────────────────────────────────────────────────────────────────
# 4) `transformar()` actualiza (no salta) un paso con la v1 vieja
# ─────────────────────────────────────────────────────────────────────────

def _cfg_minimo(paso_canonizacion_existente=None):
    """Config mínima del pipeline 21 con los pasos que `transformar()` toca."""
    pasos = [
        {"step": "RunExcelETL", "params": {"output_key": "estudiantes_raw"}},
    ]
    if paso_canonizacion_existente is not None:
        pasos.append(paso_canonizacion_existente)
    pasos += [
        {"step": "RunDIAPDFExtraction", "params": {"output_key": "preguntas_raw"}},
        {
            "step": "ApplyDerivedFields",
            "params": {
                "output_key": "estudiantes_derived",
                "derived_fields": [
                    {"kind": "normalize_name", "name": "Nombre_Norm", "value_field": "Nombre"},
                    {"kind": "row_mean_dynamic", "name": "Logro", "exclude_columns": []},
                    {"kind": "agg", "name": "Logro Promedio", "entity_field": ["Curso", "Nombre_Norm"]},
                ],
            },
        },
        {"step": "SaveToMetric", "params": {"metric_id": 6}},
        {"step": "SaveToMetric", "params": {"metric_id": 7}},
    ]
    return {"pipeline": pasos}


def test_transformar_inserta_canonizacion_si_no_existe():
    cfg = _cfg_minimo()
    nuevo, notas = transformar(cfg)
    verificar(nuevo)  # no debe lanzar
    assert any("insertado ModifyColumnValues tras RunExcelETL" in n for n in notas)
    assert any("insertado ModifyColumnValues tras RunDIAPDFExtraction" in n for n in notas)


def test_transformar_actualiza_paso_v1_existente_en_vez_de_saltarlo():
    paso_v1 = paso_canonico("estudiantes_raw")
    paso_v1["params"]["transformations"] = [copy.deepcopy(_TRANSFORMACION_V1_HISTORICA)]
    assert MARCA in paso_v1["description"]

    cfg = _cfg_minimo(paso_canonizacion_existente=paso_v1)
    nuevo, notas = transformar(cfg)
    verificar(nuevo)

    assert any("estudiantes_raw: canonización actualizada a la versión vigente" in n for n in notas)
    # el paso sigue en su lugar (no se duplicó) y ahora trae la v2
    pasos_canon = [
        s for s in nuevo["pipeline"]
        if s["step"] == "ModifyColumnValues" and s["params"]["input_key"] == "estudiantes_raw"
    ]
    assert len(pasos_canon) == 1
    assert pasos_canon[0]["params"]["transformations"] == [TRANSFORMACION]


def test_transformar_no_toca_paso_ya_en_version_vigente():
    paso_v2 = paso_canonico("estudiantes_raw")
    cfg = _cfg_minimo(paso_canonizacion_existente=paso_v2)
    nuevo, notas = transformar(cfg)
    verificar(nuevo)
    assert any("estudiantes_raw: canonización ya estaba en la versión vigente" in n for n in notas)


def test_transformar_lee_xls_por_start_marker():
    """El XLS se lee por el texto del encabezado y no por fila fija: RunExcelETL
    descarta así la fila de promedio sin N° de lista de los .xlsx de Panguipulli
    2024. Idempotente: una segunda pasada no reporta ese cambio."""
    cfg = _cfg_minimo()
    cfg["pipeline"][0]["params"]["header_row"] = 12
    out, notas = transformar(cfg)
    p = next(s["params"] for s in out["pipeline"] if s["step"] == "RunExcelETL")
    assert p["start_marker"] == START_MARKER
    assert p["header_offset"] == 0
    assert "header_row" not in p
    assert any("start_marker" in n for n in notas)
    _, notas2 = transformar(out)
    assert not any("start_marker" in n for n in notas2)
