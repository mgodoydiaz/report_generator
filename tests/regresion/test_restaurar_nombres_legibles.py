"""Tests de `scripts/restaurar_nombres_legibles.py`.

Contexto: el backfill de julio copió `Nombre_Norm` sobre `Nombre` cuando el
original faltaba, dejando filas con el nombre en formato normalizado
("GONZALEZ JUAN PEREZ"). El script restaura el nombre legible desde otras
filas de la misma org (misma clave normalizada o mismo RUT).

Casos cubiertos:
  - restaurable (variante más frecuente gana; Nombre_Norm queda intacta)
  - sin candidato (ninguna fila legible normaliza a la clave)
  - RUT (desambigua un empate de frecuencia+largo entre variantes)
  - invariante violada (el candidato vía RUT normaliza a OTRA clave)
  - dry-run por defecto no escribe; --apply exige respaldo previo
  - multi-tenancy (no se cruzan nombres entre organizaciones)
"""
from __future__ import annotations

import csv
import json
from collections import Counter

import pytest

from tests.factories import (
    make_dimension,
    make_metric,
    make_metric_data,
    make_org,
)

pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────

def _montar(db, org, *, con_rut=True):
    """Dos métricas (objetivo + fuente) que comparten Nombre/Nombre_Norm/RUT."""
    dim_nombre = make_dimension(db, org, name="Nombre")
    dim_norm = make_dimension(db, org, name="Nombre_Norm")
    dims = [dim_nombre, dim_norm]
    dim_rut = None
    if con_rut:
        dim_rut = make_dimension(db, org, name="RUT")
        dims.append(dim_rut)
    m_obj = make_metric(db, org, name="Cálculo Veloz", dimensions=dims)
    m_src = make_metric(db, org, name="DIA por estudiante", dimensions=dims)
    claves = {
        "n": str(dim_nombre.id_dimension),
        "nn": str(dim_norm.id_dimension),
        "r": str(dim_rut.id_dimension) if dim_rut else None,
    }
    return m_obj, m_src, claves


def _fila_rota(db, metric, claves, clave_norm, *, rut=None):
    """Fila objetivo: Nombre == Nombre_Norm (formato normalizado)."""
    dims = {claves["n"]: clave_norm, claves["nn"]: clave_norm}
    if rut:
        dims[claves["r"]] = rut
    return make_metric_data(db, metric, value=0.5, dimensions_json=dims)


def _fila_fuente(db, metric, claves, nombre, *, rut=None, norm=None):
    """Fila fuente con Nombre legible (y opcionalmente RUT / Nombre_Norm)."""
    dims = {claves["n"]: nombre}
    if norm:
        dims[claves["nn"]] = norm
    if rut:
        dims[claves["r"]] = rut
    return make_metric_data(db, metric, value=0.7, dimensions_json=dims)


def _dims_de(fila):
    return json.loads(fila.dimensions_json)


# ─────────────────────────────────────────────────────────────────────────
# Regla de elección (unidad, sin DB)
# ─────────────────────────────────────────────────────────────────────────

class TestElegir:

    def test_gana_la_mas_frecuente(self):
        from scripts.restaurar_nombres_legibles import _elegir

        ganador, _ = _elegir(Counter({"José Pérez": 3, "Jose Perez": 1}))
        assert ganador == "José Pérez"

    def test_empate_de_frecuencia_gana_la_mas_larga(self):
        from scripts.restaurar_nombres_legibles import _elegir

        ganador, _ = _elegir(Counter({"Juan Pérez": 2, "Juan Pérez Soto": 2}))
        assert ganador == "Juan Pérez Soto"

    def test_empate_total_no_hay_ganador(self):
        from scripts.restaurar_nombres_legibles import _elegir

        # Misma frecuencia y mismo largo, strings distintos → ambigua.
        ganador, finalistas = _elegir(
            Counter({"Juan González Pérez": 1, "González Juan Pérez": 1})
        )
        assert ganador is None
        assert len(finalistas) == 2


# ─────────────────────────────────────────────────────────────────────────
# Flujo completo contra la DB
# ─────────────────────────────────────────────────────────────────────────

class TestRestaurarNombresLegibles:

    def test_restaura_la_variante_mas_frecuente_y_norm_queda_intacta(
        self, db_session, tmp_path
    ):
        from scripts.restaurar_nombres_legibles import restaurar

        org = make_org(db_session)
        m_obj, m_src, claves = _montar(db_session, org)
        rota = _fila_rota(db_session, m_obj, claves, "JOSE PEREZ")
        _fila_fuente(db_session, m_src, claves, "Jose Perez")
        _fila_fuente(db_session, m_src, claves, "José Pérez", norm="JOSE PEREZ")
        _fila_fuente(db_session, m_src, claves, "José Pérez", norm="JOSE PEREZ")

        backup = tmp_path / "respaldo.csv"
        resumen = restaurar(
            db_session, org.id, aplicar=True, backup_path=backup
        )

        assert resumen["objetivo"] == 1
        assert resumen["restauradas"] == 1
        assert resumen["sin_candidato"] == 0
        assert resumen["ambiguas"] == 0
        assert resumen["invariante_violada"] == 0
        assert resumen["por_metrica"][m_obj.id_metric]["restauradas"] == 1

        db_session.refresh(rota)
        d = _dims_de(rota)
        assert d[claves["n"]] == "José Pérez"       # la más frecuente (2 vs 1)
        assert d[claves["nn"]] == "JOSE PEREZ"      # Nombre_Norm intacta

        # El respaldo previo existe y trae el JSON original de la fila.
        with open(backup, encoding="utf-8") as f:
            filas = list(csv.DictReader(f))
        assert len(filas) == 1
        assert filas[0]["id_data"] == str(rota.id_data)
        assert json.loads(filas[0]["dimensions_json"])[claves["n"]] == "JOSE PEREZ"

    def test_sin_candidato_no_toca_la_fila_y_se_reporta(
        self, db_session, tmp_path
    ):
        from scripts.restaurar_nombres_legibles import restaurar

        org = make_org(db_session)
        m_obj, m_src, claves = _montar(db_session, org)
        rota = _fila_rota(db_session, m_obj, claves, "NADIE CONOCIDO")
        # Fuente legible pero de OTRO estudiante (otra clave normalizada).
        _fila_fuente(db_session, m_src, claves, "Pedro Páramo")

        report = tmp_path / "no_restauradas.csv"
        resumen = restaurar(
            db_session, org.id, aplicar=True,
            backup_path=tmp_path / "b.csv", report_path=report,
        )

        assert resumen["objetivo"] == 1
        assert resumen["restauradas"] == 0
        assert resumen["sin_candidato"] == 1

        db_session.refresh(rota)
        assert _dims_de(rota)[claves["n"]] == "NADIE CONOCIDO"

        with open(report, encoding="utf-8") as f:
            filas = list(csv.DictReader(f))
        assert len(filas) == 1
        assert filas[0]["id_data"] == str(rota.id_data)
        assert filas[0]["motivo"] == "sin_candidato"

    def test_rut_desambigua_empate_entre_variantes(self, db_session, tmp_path):
        """Dos variantes legibles empatan en frecuencia y largo (mismas
        palabras en distinto orden). Sin RUT la fila queda ambigua; con RUT
        se restaura la variante que acompaña a ese RUT."""
        from scripts.restaurar_nombres_legibles import restaurar

        org = make_org(db_session)
        m_obj, m_src, claves = _montar(db_session, org)
        con_rut = _fila_rota(
            db_session, m_obj, claves, "GONZALEZ JUAN PEREZ", rut="1-1"
        )
        sin_rut = _fila_rota(db_session, m_obj, claves, "GONZALEZ JUAN PEREZ")
        # Ambas normalizan a "GONZALEZ JUAN PEREZ" y miden lo mismo.
        _fila_fuente(
            db_session, m_src, claves, "Juan González Pérez", rut="1-1"
        )
        _fila_fuente(
            db_session, m_src, claves, "González Juan Pérez", rut="2-2"
        )

        resumen = restaurar(
            db_session, org.id, aplicar=True, backup_path=tmp_path / "b.csv"
        )

        assert resumen["objetivo"] == 2
        assert resumen["restauradas"] == 1
        assert resumen["ambiguas"] == 1

        db_session.refresh(con_rut)
        db_session.refresh(sin_rut)
        assert _dims_de(con_rut)[claves["n"]] == "Juan González Pérez"
        assert _dims_de(sin_rut)[claves["n"]] == "GONZALEZ JUAN PEREZ"

        fuentes = {r[0]: r[4] for r in resumen["restauraciones"]}
        assert fuentes[con_rut.id_data] == "rut"

    def test_invariante_violada_aborta_la_fila(self, db_session, tmp_path):
        """El candidato vía RUT normaliza a OTRA clave: escribirlo rompería
        la coherencia Nombre/Nombre_Norm, así que la fila se aborta."""
        from scripts.restaurar_nombres_legibles import restaurar

        org = make_org(db_session)
        m_obj, m_src, claves = _montar(db_session, org)
        rota = _fila_rota(
            db_session, m_obj, claves, "PEREZ QUIRQUINCHO", rut="3-3"
        )
        # Mismo RUT, nombre legible, pero normaliza a "MARIA NANDU".
        _fila_fuente(db_session, m_src, claves, "María Ñandú", rut="3-3")

        report = tmp_path / "report.csv"
        resumen = restaurar(
            db_session, org.id, aplicar=True,
            backup_path=tmp_path / "b.csv", report_path=report,
        )

        assert resumen["objetivo"] == 1
        assert resumen["restauradas"] == 0
        assert resumen["invariante_violada"] == 1

        db_session.refresh(rota)
        d = _dims_de(rota)
        assert d[claves["n"]] == "PEREZ QUIRQUINCHO"   # intacta
        assert d[claves["nn"]] == "PEREZ QUIRQUINCHO"  # intacta

        with open(report, encoding="utf-8") as f:
            filas = list(csv.DictReader(f))
        assert filas[0]["motivo"] == "invariante_violada"

    def test_dry_run_por_defecto_no_escribe(self, db_session):
        from scripts.restaurar_nombres_legibles import restaurar

        org = make_org(db_session)
        m_obj, m_src, claves = _montar(db_session, org)
        rota = _fila_rota(db_session, m_obj, claves, "JOSE PEREZ")
        _fila_fuente(db_session, m_src, claves, "José Pérez")

        resumen = restaurar(db_session, org.id)  # aplicar=False por defecto

        # El resumen reporta lo que HARÍA...
        assert resumen["restauradas"] == 1
        assert resumen["restauraciones"][0][3] == "José Pérez"

        # ...pero la DB no cambió.
        db_session.rollback()
        db_session.refresh(rota)
        assert _dims_de(rota)[claves["n"]] == "JOSE PEREZ"

    def test_apply_sin_respaldo_lanza_error(self, db_session):
        from scripts.restaurar_nombres_legibles import restaurar

        org = make_org(db_session)
        _montar(db_session, org)

        with pytest.raises(ValueError, match="respaldo"):
            restaurar(db_session, org.id, aplicar=True, backup_path=None)

    def test_multi_tenancy_no_cruza_organizaciones(self, db_session, tmp_path):
        """El nombre legible existe solo en OTRA org: no debe usarse."""
        from scripts.restaurar_nombres_legibles import restaurar

        org_a = make_org(db_session)
        org_b = make_org(db_session)
        _, m_src_a, claves_a = _montar(db_session, org_a)
        m_obj_b, _, claves_b = _montar(db_session, org_b)

        _fila_fuente(db_session, m_src_a, claves_a, "José Pérez")
        rota_b = _fila_rota(db_session, m_obj_b, claves_b, "JOSE PEREZ")

        resumen = restaurar(
            db_session, org_b.id, aplicar=True, backup_path=tmp_path / "b.csv"
        )

        assert resumen["objetivo"] == 1
        assert resumen["restauradas"] == 0
        assert resumen["sin_candidato"] == 1

        db_session.refresh(rota_b)
        assert _dims_de(rota_b)[claves_b["n"]] == "JOSE PEREZ"

    def test_org_sin_dimensiones_sale_limpio(self, db_session):
        from scripts.restaurar_nombres_legibles import restaurar

        org = make_org(db_session)
        make_metric(db_session, org, name="Otra métrica")

        assert restaurar(db_session, org.id) is None
