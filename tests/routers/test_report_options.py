"""Tests de GET /api/indicators/{id}/report-options y del campo report_engine_type.

Contrato vigente (Fase 2 del selector de informes):

    {
      "indicator_id", "engine_type", "engine_type_origen",
      "grupos": {"periodo": [4 cards], "especializados": [custom]},
      "dimensiones_filtrables": [{"id_dimension", "name", "values"}],
      "opciones": [...]   # plano periodo + especializados (compat)
    }

Las 4 cards de período se resuelven contra los datos REALES del indicador
(ver `backend/rgenerator/reports/periodos.py`), por eso los fixtures cargan
`metric_data` con el año en curso.
"""
from __future__ import annotations

import json
from datetime import date

import pytest

from backend.rgenerator.reports.periodos import NUMERO_A_MES, semestre_de_mes
from tests.factories import (
    make_dimension, make_indicator, make_metric, make_metric_data, make_org,
)

LAYOUT_EVAL = json.dumps({"sections": [{"type": "kpi"}]})
LAYOUT_HIST = json.dumps({"sections": [{"type": "line"}]})


def _opciones_por_id(body):
    return {o["id"]: o for o in body["opciones"]}


def _cards_por_id(body):
    return {o["id"]: o for o in body["grupos"]["periodo"]}


@pytest.fixture
def hoy():
    return date.today()


@pytest.fixture
def indicador_con_datos(db_session, org, hoy):
    """Indicador SIMCE con Curso/Año/Mes/N Prueba y datos del año en curso.

    Dos filas: una del año pasado (ABRIL, prueba 1) y una del mes actual
    (prueba 3) — así `ultima_prueba`, `semestral` y `anual` resuelven.
    """
    dims = {n: make_dimension(db_session, org, name=n)
            for n in ("Curso", "Año", "Mes", "N Prueba")}
    metric = make_metric(
        db_session, org,
        name="Resultados SIMCE por Estudiante",
        data_type="object",
        fields=[{"name": "Logro", "type": "float"}],
        dimensions=list(dims.values()),
    )
    ident = {n: str(d.id_dimension) for n, d in dims.items()}
    mes_actual = NUMERO_A_MES[hoy.month]

    make_metric_data(db_session, metric, value={"Logro": 0.4}, dimensions_json={
        ident["Curso"]: "II A", ident["Año"]: str(hoy.year - 1),
        ident["Mes"]: "ABRIL", ident["N Prueba"]: "1",
    })
    make_metric_data(db_session, metric, value={"Logro": 0.7}, dimensions_json={
        ident["Curso"]: "II B", ident["Año"]: str(hoy.year),
        ident["Mes"]: mes_actual, ident["N Prueba"]: "3",
    })

    ind = make_indicator(
        db_session, org, name="SIMCE Lenguaje", metrics=[metric],
        report_engine_type="simce",
        pdf_layout=LAYOUT_EVAL,
        pdf_layout_historico=LAYOUT_HIST,
    )
    ind._dims = dims  # atajo para los tests
    return ind


@pytest.mark.integration
class TestReportOptionsEstructura:
    def test_cross_org_404(self, client_auth, db_session):
        otra = make_org(db_session, name="Org Ajena RO")
        ajeno = make_indicator(db_session, otra, name="Ajeno")
        resp = client_auth.get(f"/api/indicators/{ajeno.id_indicator}/report-options")
        assert resp.status_code == 404

    def test_claves_de_primer_nivel(self, client_auth, indicador_con_datos):
        body = client_auth.get(
            f"/api/indicators/{indicador_con_datos.id_indicator}/report-options"
        ).json()
        assert set(body) == {
            "indicator_id", "engine_type", "engine_type_origen",
            "grupos", "dimensiones_filtrables", "opciones",
        }
        assert set(body["grupos"]) == {"periodo", "especializados"}

    def test_opciones_es_la_concatenacion_plana(self, client_auth, indicador_con_datos):
        body = client_auth.get(
            f"/api/indicators/{indicador_con_datos.id_indicator}/report-options"
        ).json()
        esperado = body["grupos"]["periodo"] + body["grupos"]["especializados"]
        assert body["opciones"] == esperado

    def test_las_cuatro_cards_con_labels_exactos(self, client_auth, indicador_con_datos):
        body = client_auth.get(
            f"/api/indicators/{indicador_con_datos.id_indicator}/report-options"
        ).json()
        cards = body["grupos"]["periodo"]
        assert [c["id"] for c in cards] == [
            "periodo_ultima_prueba", "periodo_semestral",
            "periodo_anual", "periodo_personalizado",
        ]
        assert [c["label"] for c in cards] == [
            "Informe última prueba", "Informe semestral",
            "Informe Anual", "Informe Personalizado",
        ]

    def test_invocacion_de_las_cards_manda_periodo(self, client_auth, indicador_con_datos):
        iid = indicador_con_datos.id_indicator
        cards = _cards_por_id(
            client_auth.get(f"/api/indicators/{iid}/report-options").json()
        )
        for card_id, tipo in (
            ("periodo_ultima_prueba", "ultima_prueba"),
            ("periodo_semestral", "semestral"),
            ("periodo_anual", "anual"),
            ("periodo_personalizado", "personalizado"),
        ):
            card = cards[card_id]
            assert card["periodo"] == {"tipo": tipo}
            assert card["invocacion"]["endpoint"] == f"/api/indicators/{iid}/export-pdf"
            assert card["invocacion"]["params"] == {"periodo": {"tipo": tipo}}
            assert card["formato"] == "pdf"
            # Motor único: el indicador es `report_engine_type="simce"` y el
            # módulo `reports/custom/simce.py` declara los 4 modos, así que
            # las cards las sirve él (contrato §2.5a). Sin módulo el motor
            # sigue siendo "weasyprint" — lo cubre test_despacho_modos.py.
            assert card["motor"] == "custom:simce"

    def test_personalizado_requiere_configuracion(self, client_auth, indicador_con_datos):
        cards = _cards_por_id(
            client_auth.get(
                f"/api/indicators/{indicador_con_datos.id_indicator}/report-options"
            ).json()
        )
        assert cards["periodo_personalizado"]["requiere_configuracion"] is True
        # las otras tres NO lo declaran
        for cid in ("periodo_ultima_prueba", "periodo_semestral", "periodo_anual"):
            assert "requiere_configuracion" not in cards[cid]


@pytest.mark.integration
class TestReportOptionsDisponibilidad:
    def test_todas_disponibles_con_layouts_y_datos(self, client_auth, indicador_con_datos, hoy):
        cards = _cards_por_id(
            client_auth.get(
                f"/api/indicators/{indicador_con_datos.id_indicator}/report-options"
            ).json()
        )
        for cid, card in cards.items():
            assert card["disponible"] is True, (cid, card["motivo_no_disponible"])
            assert card["motivo_no_disponible"] is None

    def test_descripciones_traen_el_periodo_resuelto(self, client_auth, indicador_con_datos, hoy):
        cards = _cards_por_id(
            client_auth.get(
                f"/api/indicators/{indicador_con_datos.id_indicator}/report-options"
            ).json()
        )
        mes_actual = NUMERO_A_MES[hoy.month]
        ultima = cards["periodo_ultima_prueba"]["descripcion"]
        assert ultima.startswith("Última evaluación registrada:")
        assert mes_actual in ultima and str(hoy.year) in ultima

        assert cards["periodo_anual"]["descripcion"] == f"Evolución del año {hoy.year}."

        semestre = "1er" if semestre_de_mes(hoy.month) == 1 else "2º"
        assert f"{semestre} semestre {hoy.year}" in cards["periodo_semestral"]["descripcion"]

    def test_tipo_layout_resuelto_por_card(self, client_auth, indicador_con_datos):
        cards = _cards_por_id(
            client_auth.get(
                f"/api/indicators/{indicador_con_datos.id_indicator}/report-options"
            ).json()
        )
        assert cards["periodo_ultima_prueba"]["tipo_layout"] == "evaluacion"
        assert cards["periodo_semestral"]["tipo_layout"] == "historico"
        assert cards["periodo_anual"]["tipo_layout"] == "historico"

    def test_sin_layouts_todas_no_disponibles_con_motivo_accionable(
        self, client_auth, db_session, org
    ):
        ind = make_indicator(db_session, org, name="Asistencia Mensual")
        body = client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options").json()
        assert body["engine_type"] is None
        for card in body["grupos"]["periodo"]:
            assert card["disponible"] is False
            assert "Editor de Layout" in card["motivo_no_disponible"]

    def test_ultima_prueba_requiere_layout_evaluacion(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="Solo Historico",
                             pdf_layout_historico=LAYOUT_HIST)
        cards = _cards_por_id(
            client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options").json()
        )
        assert cards["periodo_ultima_prueba"]["disponible"] is False
        assert "por evaluación" in cards["periodo_ultima_prueba"]["motivo_no_disponible"]

    def test_semestral_y_anual_requieren_layout_historico(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="Solo Evaluacion",
                             pdf_layout=LAYOUT_EVAL)
        cards = _cards_por_id(
            client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options").json()
        )
        for cid in ("periodo_semestral", "periodo_anual"):
            assert cards[cid]["disponible"] is False
            assert "histórico" in cards[cid]["motivo_no_disponible"]

    def test_personalizado_basta_con_un_layout(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="Solo Evaluacion",
                             pdf_layout=LAYOUT_EVAL)
        cards = _cards_por_id(
            client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options").json()
        )
        assert cards["periodo_personalizado"]["disponible"] is True

    def test_con_layouts_pero_sin_datos_motivo_sin_datos(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="Sin Datos",
                             pdf_layout=LAYOUT_EVAL, pdf_layout_historico=LAYOUT_HIST)
        cards = _cards_por_id(
            client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options").json()
        )
        for cid in ("periodo_ultima_prueba", "periodo_semestral", "periodo_anual"):
            assert cards[cid]["disponible"] is False
            assert cards[cid]["motivo_no_disponible"] == "Sin datos cargados para este indicador."
        # El personalizado no depende de los datos (el usuario elige el rango)
        assert cards["periodo_personalizado"]["disponible"] is True

    def test_sin_dimension_temporal_motivo_explicativo(self, client_auth, db_session, org):
        dim = make_dimension(db_session, org, name="Curso")
        metric = make_metric(
            db_session, org, name="Asistencia por Estudiante",
            data_type="float", dimensions=[dim],
        )
        make_metric_data(db_session, metric, value=0.9,
                         dimensions_json={str(dim.id_dimension): "II A"})
        ind = make_indicator(db_session, org, name="Asistencia", metrics=[metric],
                             pdf_layout=LAYOUT_EVAL, pdf_layout_historico=LAYOUT_HIST)
        cards = _cards_por_id(
            client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options").json()
        )
        assert cards["periodo_ultima_prueba"]["disponible"] is False
        assert "dimensión temporal" in cards["periodo_ultima_prueba"]["motivo_no_disponible"]
        assert "dimensión de año" in cards["periodo_anual"]["motivo_no_disponible"]


@pytest.mark.integration
class TestReportOptionsEspecializados:
    def test_engine_type_inferido_por_nombre(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="SIMCE Lenguaje 2026")
        body = client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options").json()
        assert body["engine_type"] == "simce"
        assert body["engine_type_origen"] == "inferido"
        ops = _opciones_por_id(body)
        assert ops["custom_simce"]["disponible"] is True
        assert ops["custom_simce"]["motor"] == "custom"
        assert ops["custom_simce"]["nombre"] == "simce"
        assert "Mes" in ops["custom_simce"]["requiere_filtro_temporal"]
        assert ops["custom_simce"]["invocacion"]["endpoint"] == "/api/reports/custom/simce"
        assert ops["custom_simce"]["invocacion"]["params"] == {
            "indicator_id": ind.id_indicator
        }

    def test_campo_explicito_gana_al_nombre(self, client_auth, db_session, org):
        # El nombre sugiere SIMCE pero el campo dice dia → manda el campo (fix H5)
        ind = make_indicator(
            db_session, org, name="Comparativo DIA-SIMCE",
            report_engine_type="dia",
        )
        body = client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options").json()
        assert body["engine_type"] == "dia"
        assert body["engine_type_origen"] == "campo"
        ops = _opciones_por_id(body)
        assert "custom_dia" in ops
        assert "custom_simce" not in ops
        assert ops["custom_dia"]["requiere_filtro_temporal"] == ["Hito", "Año"]

    def test_pdl_idel_agrega_opcion_especializada(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="Lectura", report_engine_type="pdl_idel")
        body = client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options").json()
        ops = _opciones_por_id(body)
        assert ops["custom_pdl_idel"]["disponible"] is True
        assert ops["custom_pdl_idel"]["label"] == "Informe PDL IDEL-Woodcock"
        assert ops["custom_pdl_idel"]["requiere_filtro_temporal"] == []

    def test_indicador_generico_no_trae_informes_custom(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="Asistencia Mensual")
        body = client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options").json()
        assert not any(o["motor"] == "custom" for o in body["opciones"])

    def test_informes_word_pospuestos_no_aparecen(self, client_auth, db_session, org):
        """Los informes Word quedan pospuestos (decisión del dueño 2026-07-30):
        el selector ya no debe ofrecerlos, aunque el registro y los endpoints
        `POST /api/reports/word/*` sigan intactos."""
        ind = make_indicator(db_session, org, name="Asistencia Mensual")
        body = client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options").json()
        word = [o for o in body["grupos"]["especializados"] if o["formato"] == "word"]
        assert word == []
        assert not any(o.get("formato") == "word" for o in body["opciones"])


@pytest.mark.integration
class TestDimensionesFiltrables:
    def test_trae_dimensiones_con_valores_reales(self, client_auth, indicador_con_datos, hoy):
        body = client_auth.get(
            f"/api/indicators/{indicador_con_datos.id_indicator}/report-options"
        ).json()
        dims = {d["name"]: d for d in body["dimensiones_filtrables"]}
        assert set(dims) == {"Curso", "Año", "Mes", "N Prueba"}
        assert dims["Curso"]["values"] == ["II A", "II B"]
        assert dims["Año"]["values"] == [str(hoy.year - 1), str(hoy.year)]
        assert all(isinstance(d["id_dimension"], int) for d in dims.values())

    def test_indicador_sin_metrics_lista_vacia(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="Vacio")
        body = client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options").json()
        assert body["dimensiones_filtrables"] == []

    def test_no_filtra_dimensiones_de_otra_org(self, client_auth, db_session, org):
        """Las dimensiones de otra org nunca aparecen (defensa multi-tenant)."""
        otra = make_org(db_session, name="Org Ajena Dims")
        dim_ajena = make_dimension(db_session, otra, name="Curso Ajeno")
        dim_propia = make_dimension(db_session, org, name="Curso")
        metric = make_metric(db_session, org, name="M por Estudiante",
                             dimensions=[dim_propia, dim_ajena])
        ind = make_indicator(db_session, org, name="Mixto", metrics=[metric])
        body = client_auth.get(f"/api/indicators/{ind.id_indicator}/report-options").json()
        nombres = {d["name"] for d in body["dimensiones_filtrables"]}
        assert nombres == {"Curso"}


@pytest.mark.integration
class TestReportEngineTypeCRUD:
    def test_create_persiste_campo(self, client_auth):
        resp = client_auth.post("/api/indicators/", json={
            "name": "Nuevo IDEL", "type": "Evaluación",
            "report_engine_type": "pdl_idel", "metric_ids": [],
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["report_engine_type"] == "pdl_idel"

    def test_update_setea_y_limpia_campo(self, client_auth, db_session, org):
        ind = make_indicator(db_session, org, name="Editable")
        base = {"name": "Editable", "type": "Evaluación"}

        resp = client_auth.put(
            f"/api/indicators/{ind.id_indicator}",
            json={**base, "report_engine_type": "simce"},
        )
        assert resp.status_code == 200
        db_session.refresh(ind)
        assert ind.report_engine_type == "simce"

        # "" explícito limpia el campo → vuelve a genérico
        resp = client_auth.put(
            f"/api/indicators/{ind.id_indicator}",
            json={**base, "report_engine_type": ""},
        )
        assert resp.status_code == 200
        db_session.refresh(ind)
        assert ind.report_engine_type is None
