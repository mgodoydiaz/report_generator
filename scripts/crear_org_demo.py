"""crear_org_demo.py — crea la organización sandbox "Colegio Demo".

Objetivo: tener una organización completa y autocontenida para probar
dashboards, gráficos e informes PDF SIN tocar los datos reales de la
fundación. Todo lo que crea el script queda bajo el `org_id` de la org
demo; jamás escribe en otra organización.

Qué crea
--------
  * Organización "Colegio Demo" (slug `colegio-demo`) + usuario admin.
  * 15 dimensiones con sus catálogos de valores.
  * 4 métricas (estudiantes + preguntas, para SIMCE y para DIA) con datos
    sintéticos deterministas (`random.seed(42)`).
  * 2 indicadores listos para informe y dashboard:
      - "SIMCE Demo Lenguaje" (report_engine_type='simce')
      - "DIA Demo Lectura"    (report_engine_type='dia')
  * Catálogo de gráficos y tablas (Specs) propio de la org demo, con los
    `metric_id` / `indicator_id` de la org demo — nunca ids de otra org.

Edge cases deliberados (los mismos que aparecen en los datos reales):
  * DIA — un pequeño % de filas de preguntas con `Eje Temático` nulo.
  * DIA — dos estudiantes con `Nombre` nulo pero `Nombre_Norm` poblado
    (por eso las derived_columns de DIA usan `Nombre_Norm` como entidad).

Uso
---
    # dentro del contenedor de dev (DB canónica del compose)
    docker compose -f docker-compose.dev.yml exec -T backend \\
        python scripts/crear_org_demo.py [--reset]

Sin `--reset` aborta si la org demo ya existe. Con `--reset` borra TODO lo
de la org demo y la recrea desde cero (idempotente).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

# Dentro del contenedor el repo vive en /app; fuera, la raíz es el padre de scripts/.
_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from backend.auditing import make_metric_data              # noqa: E402
from backend.auth import hash_password                     # noqa: E402
from backend.database import SessionLocal                  # noqa: E402
from backend.models import (                               # noqa: E402
    ApiKey,
    Dimension,
    DimensionValue,
    Indicator,
    IndicatorMetric,
    IngestLog,
    Metric,
    MetricData,
    MetricDimension,
    Organization,
    OrganizationAsset,
    Pipeline,
    Spec,
    User,
)

# ═════════════════════════════════════════════════════════════════════════
# Constantes de la org demo
# ═════════════════════════════════════════════════════════════════════════

SLUG_DEMO = "colegio-demo"
NOMBRE_DEMO = "Colegio Demo"
DESCRIPCION_DEMO = (
    "Organización de prueba (sandbox). Datos 100% sintéticos generados por "
    "scripts/crear_org_demo.py — no contiene información real de ningún "
    "establecimiento."
)

EMAIL_ADMIN = "demo@rgenerator.local"
NOMBRE_ADMIN = "Admin Demo"
PASSWORD_ADMIN = "demo1234"

SEMILLA = 42
VIA_CARGA = "api_direct"  # created_via de metric_data (ver backend/auditing.py)

# ── SIMCE Demo Lenguaje ──────────────────────────────────────────────────
CURSOS_SIMCE = ("1° Medio A", "1° Medio B")
ESTUDIANTES_POR_CURSO = 15
ASIGNATURA_SIMCE = "LENGUAJE"
NIVEL_SIMCE = "MEDIA"

# (Año, Mes, N Prueba) — N Prueba es correlativo dentro del año.
EVALUACIONES_SIMCE = (
    ("2025", "ABRIL", "1"),
    ("2025", "JULIO", "2"),
    ("2025", "NOVIEMBRE", "3"),
    ("2026", "ABRIL", "1"),
    ("2026", "JULIO", "2"),
)

NIVELES_SIMCE = ("Insuficiente", "Elemental", "Adecuado")
# Cortes sobre el puntaje SIMCE estimado (rango generado ≈ 250–350).
CORTE_SIMCE_INSUFICIENTE = 285
CORTE_SIMCE_ELEMENTAL = 315

EJES_SIMCE = ("TEXTO NARRATIVO", "TEXTO INFORMATIVO", "TEXTO ARGUMENTATIVO")

# ── DIA Demo Lectura ─────────────────────────────────────────────────────
CURSOS_DIA = ("3° Básico A", "3° Básico B")
ASIGNATURA_DIA = "LECTURA"
NIVEL_DIA = "BÁSICA"

# (Año, Hito) — 5° y 6° no rinden cierre, acá el 2026 va recién en diagnóstico.
EVALUACIONES_DIA = (
    ("2025", "DIAGNOSTICO"),
    ("2025", "INTERMEDIO"),
    ("2025", "CIERRE"),
    ("2026", "DIAGNOSTICO"),
)

NIVELES_DIA = ("Inicial", "Intermedio", "Avanzado")
CORTE_DIA_INICIAL = 0.45
CORTE_DIA_INTERMEDIO = 0.70

EJES_DIA = ("COMPRENSIÓN LITERAL", "COMPRENSIÓN INFERENCIAL", "REFLEXIÓN Y EVALUACIÓN")

# Índices (1-based, dentro de la nómina DIA) de los estudiantes que quedan
# con `Nombre` nulo — reproduce el caso real en que la planilla de origen
# viene sin la columna nombre y solo se puede identificar por Nombre_Norm.
ESTUDIANTES_DIA_SIN_NOMBRE = (5, 22)
# Proporción de filas de preguntas DIA con Eje Temático nulo.
PROB_EJE_NULO_DIA = 0.08

# ── Comunes ──────────────────────────────────────────────────────────────
HABILIDADES = (
    "LOCALIZAR INFORMACIÓN",
    "INTERPRETAR Y RELACIONAR",
    "REFLEXIONAR SOBRE EL TEXTO",
)
N_PREGUNTAS = 10
LETRAS = ("A", "B", "C", "D")

COLORES_SEMAFORO = ("#dc2626", "#eab308", "#22c55e")

ESCALA_DIVERGENTE = {
    "kind": "diverging",
    "min_color": "#ef4444",
    "neutral_color": "#fef3c7",
    "max_color": "#22c55e",
    "midpoint": 0.5,
}


# ═════════════════════════════════════════════════════════════════════════
# Catálogo de dimensiones
# ═════════════════════════════════════════════════════════════════════════

DIMENSIONES: tuple[dict, ...] = (
    {"name": "Año", "data_type": "int", "valores": ["2025", "2026"],
     "description": "Año de aplicación de la evaluación."},
    {"name": "Curso", "validation_mode": "list",
     "valores": [*CURSOS_SIMCE, *CURSOS_DIA],
     "description": "Curso al que pertenece el estudiante."},
    {"name": "Nivel", "validation_mode": "list", "valores": [NIVEL_SIMCE, NIVEL_DIA],
     "description": "Nivel educativo agregado del curso."},
    {"name": "Asignatura", "valores": [ASIGNATURA_SIMCE, ASIGNATURA_DIA],
     "description": "Asignatura evaluada."},
    {"name": "Mes", "valores": ["ABRIL", "JULIO", "NOVIEMBRE"],
     "description": "Mes de aplicación (dimensión temporal de SIMCE)."},
    {"name": "N Prueba", "data_type": "int", "valores": ["1", "2", "3"],
     "description": "Número correlativo de la prueba dentro del año."},
    {"name": "Hito", "validation_mode": "list",
     "valores": ["DIAGNOSTICO", "INTERMEDIO", "CIERRE"],
     "description": "Hito de aplicación (dimensión temporal de DIA)."},
    {"name": "Nivel de Logro", "validation_mode": "list", "valores": list(NIVELES_SIMCE),
     "description": "Categoría de logro del estudiante en la prueba."},
    {"name": "Nombre", "description": "Nombre del estudiante (puede venir nulo)."},
    {"name": "Nombre_Norm",
     "description": "Nombre normalizado (clave estable de identidad del estudiante)."},
    {"name": "RUT", "description": "Identificador sintético del estudiante."},
    {"name": "Pregunta", "valores": [f"P{i}" for i in range(1, N_PREGUNTAS + 1)],
     "description": "Código de la pregunta (SIMCE)."},
    {"name": "N Pregunta", "data_type": "int",
     "valores": [str(i) for i in range(1, N_PREGUNTAS + 1)],
     "description": "Número de la pregunta (DIA)."},
    {"name": "Habilidad", "valores": list(HABILIDADES),
     "description": "Habilidad evaluada por la pregunta."},
    {"name": "Eje Temático", "valores": [*EJES_SIMCE, *EJES_DIA],
     "description": "Eje temático de la pregunta."},
)


# ═════════════════════════════════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════════════════════════════════

def _normalizar(texto: str) -> str:
    """'Estudiante Demo 07' → 'ESTUDIANTE DEMO 07' (sin tildes, mayúsculas)."""
    sin_tildes = (
        unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    )
    return " ".join(sin_tildes.upper().split())


def _acotar(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))


def _nivel_simce(puntaje: int) -> str:
    if puntaje < CORTE_SIMCE_INSUFICIENTE:
        return NIVELES_SIMCE[0]
    if puntaje < CORTE_SIMCE_ELEMENTAL:
        return NIVELES_SIMCE[1]
    return NIVELES_SIMCE[2]


def _nivel_dia(logro: float) -> str:
    if logro < CORTE_DIA_INICIAL:
        return NIVELES_DIA[0]
    if logro < CORTE_DIA_INTERMEDIO:
        return NIVELES_DIA[1]
    return NIVELES_DIA[2]


def _meta(descripcion: str) -> str:
    """`Spec.metadata` estándar del catálogo de charts/tablas."""
    return json.dumps(
        {
            "description": descripcion,
            "is_draft": False,
            "updated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        },
        ensure_ascii=False,
    )


def _volcar(objeto) -> str:
    return json.dumps(objeto, ensure_ascii=False)


# ═════════════════════════════════════════════════════════════════════════
# Borrado (--reset)
# ═════════════════════════════════════════════════════════════════════════

def borrar_org(db, org: Organization) -> dict[str, int]:
    """Borra TODO lo que pertenece a `org`. Devuelve conteos por tabla.

    Respeta el orden de las FKs y filtra siempre por la org — ninguna
    sentencia puede alcanzar filas de otra organización.
    """
    org_id = org.id
    conteos: dict[str, int] = {}

    ids_metricas = [
        m.id_metric for m in db.query(Metric.id_metric).filter(Metric.org_id == org_id)
    ]
    ids_dimensiones = [
        d.id_dimension
        for d in db.query(Dimension.id_dimension).filter(Dimension.org_id == org_id)
    ]
    ids_indicadores = [
        i.id_indicator
        for i in db.query(Indicator.id_indicator).filter(Indicator.org_id == org_id)
    ]

    conteos["metric_data"] = (
        db.query(MetricData).filter(MetricData.org_id == org_id)
        .delete(synchronize_session=False)
    )
    if ids_metricas:
        conteos["metric_dimensions"] = (
            db.query(MetricDimension)
            .filter(MetricDimension.id_metric.in_(ids_metricas))
            .delete(synchronize_session=False)
        )
    if ids_indicadores:
        conteos["indicator_metrics"] = (
            db.query(IndicatorMetric)
            .filter(IndicatorMetric.id_indicator.in_(ids_indicadores))
            .delete(synchronize_session=False)
        )
    conteos["metrics"] = (
        db.query(Metric).filter(Metric.org_id == org_id)
        .delete(synchronize_session=False)
    )
    if ids_dimensiones:
        conteos["dimension_values"] = (
            db.query(DimensionValue)
            .filter(DimensionValue.id_dimension.in_(ids_dimensiones))
            .delete(synchronize_session=False)
        )
    conteos["dimensions"] = (
        db.query(Dimension).filter(Dimension.org_id == org_id)
        .delete(synchronize_session=False)
    )
    conteos["indicators"] = (
        db.query(Indicator).filter(Indicator.org_id == org_id)
        .delete(synchronize_session=False)
    )
    conteos["specs"] = (
        db.query(Spec).filter(Spec.org_id == org_id).delete(synchronize_session=False)
    )
    conteos["pipelines"] = (
        db.query(Pipeline).filter(Pipeline.org_id == org_id)
        .delete(synchronize_session=False)
    )
    conteos["organization_assets"] = (
        db.query(OrganizationAsset).filter(OrganizationAsset.org_id == org_id)
        .delete(synchronize_session=False)
    )
    conteos["ingest_log"] = (
        db.query(IngestLog).filter(IngestLog.org_id == org_id)
        .delete(synchronize_session=False)
    )
    conteos["api_keys"] = (
        db.query(ApiKey).filter(ApiKey.org_id == org_id)
        .delete(synchronize_session=False)
    )
    conteos["users"] = (
        db.query(User).filter(User.org_id == org_id).delete(synchronize_session=False)
    )
    conteos["organizations"] = (
        db.query(Organization).filter(Organization.id == org_id)
        .delete(synchronize_session=False)
    )
    db.flush()
    return {k: v for k, v in conteos.items() if v}


# ═════════════════════════════════════════════════════════════════════════
# Creación de la estructura
# ═════════════════════════════════════════════════════════════════════════

def crear_org_y_admin(db) -> tuple[Organization, User]:
    org = Organization(
        name=NOMBRE_DEMO, slug=SLUG_DEMO, description=DESCRIPCION_DEMO, is_active=True
    )
    db.add(org)
    db.flush()

    admin = User(
        name=NOMBRE_ADMIN,
        email=EMAIL_ADMIN,
        password_hash=hash_password(PASSWORD_ADMIN),
        org_id=org.id,
        role="admin",
        is_active=True,
        is_superadmin=False,
    )
    db.add(admin)
    db.flush()
    return org, admin


def crear_dimensiones(db, org_id: int) -> dict[str, Dimension]:
    """Crea las dimensiones + sus valores. Devuelve {nombre: Dimension}."""
    dims: dict[str, Dimension] = {}
    for cfg in DIMENSIONES:
        dim = Dimension(
            name=cfg["name"],
            data_type=cfg.get("data_type", "str"),
            validation_mode=cfg.get("validation_mode", "free"),
            description=cfg.get("description", ""),
            org_id=org_id,
        )
        db.add(dim)
        db.flush()
        for valor in cfg.get("valores", []):
            db.add(DimensionValue(id_dimension=dim.id_dimension, value=valor, is_active=True))
        dims[cfg["name"]] = dim
    db.flush()
    return dims


def crear_metrica(
    db,
    org_id: int,
    nombre: str,
    descripcion: str,
    campos: list[dict],
    nombres_dimensiones: list[str],
    dims: dict[str, Dimension],
) -> Metric:
    """Crea una métrica `object` con sus campos y su enlace a dimensiones."""
    metrica = Metric(
        name=nombre,
        data_type="object",
        meta_json=_volcar({"fields": campos}),
        description=descripcion,
        unit="",
        org_id=org_id,
    )
    db.add(metrica)
    db.flush()
    for nombre_dim in nombres_dimensiones:
        db.add(
            MetricDimension(
                id_metric=metrica.id_metric, id_dimension=dims[nombre_dim].id_dimension
            )
        )
    db.flush()
    return metrica


def _fila(
    metrica: Metric,
    valores: dict,
    dimensiones: dict,
    dims: dict[str, Dimension],
    org_id: int,
    user_id: int,
) -> MetricData:
    """Construye una fila de metric_data con `dimensions_json` = {id: valor}."""
    dims_json = {
        str(dims[nombre].id_dimension): valor for nombre, valor in dimensiones.items()
    }
    return make_metric_data(
        metric_id=metrica.id_metric,
        value=_volcar(valores),
        dimensions=dims_json,
        org_id=org_id,
        user_id=user_id,
        via=VIA_CARGA,
    )


# ═════════════════════════════════════════════════════════════════════════
# Nóminas sintéticas
# ═════════════════════════════════════════════════════════════════════════

def generar_nomina(cursos: tuple[str, ...], indice_inicial: int, rnd: random.Random) -> list[dict]:
    """Nómina determinista: {indice, nombre, nombre_norm, rut, curso, aptitud, offset}."""
    nomina: list[dict] = []
    indice = indice_inicial
    for posicion, curso in enumerate(cursos):
        for _ in range(ESTUDIANTES_POR_CURSO):
            nombre = f"Estudiante Demo {indice:02d}"
            nomina.append(
                {
                    "indice": indice,
                    "nombre": nombre,
                    "nombre_norm": _normalizar(nombre),
                    "rut": f"DEMO-{indice:04d}",
                    "curso": curso,
                    # Aptitud latente del estudiante: mueve todos sus resultados.
                    "aptitud": rnd.gauss(0, 1),
                    # Efecto curso: separa las barras "por curso" de forma estable.
                    "offset": 0.05 * posicion,
                }
            )
            indice += 1
    return nomina


def _dificultades(rnd: random.Random) -> list[float]:
    """Ajuste de dificultad por pregunta (mismo set para todas las pruebas)."""
    return [rnd.uniform(-0.16, 0.16) for _ in range(N_PREGUNTAS)]


# ═════════════════════════════════════════════════════════════════════════
# Datos SIMCE
# ═════════════════════════════════════════════════════════════════════════

CAMPOS_SIMCE_ESTUDIANTES = [
    {"name": "Buenas", "type": "int"},
    {"name": "Malas", "type": "int"},
    {"name": "Omitidas", "type": "int"},
    {"name": "Rend", "type": "float"},
    {"name": "SIMCE", "type": "int"},
    {"name": "Nota", "type": "float"},
    {"name": "Logro", "type": "str"},
    {"name": "Puntaje", "type": "int"},
]

CAMPOS_SIMCE_PREGUNTAS = [
    {"name": "Correcta", "type": "str"},
    {"name": "Respuesta", "type": "str"},
    {"name": "Correcto", "type": "int"},
    {"name": "Logro", "type": "float"},
]

DIMS_SIMCE_ESTUDIANTES = [
    "Año", "Curso", "Nivel", "Asignatura", "Mes", "N Prueba",
    "Nombre", "Nombre_Norm", "RUT", "Nivel de Logro",
]

DIMS_SIMCE_PREGUNTAS = [
    "Año", "Curso", "Nivel", "Asignatura", "Mes", "N Prueba",
    "Nombre", "RUT", "Pregunta", "Habilidad", "Eje Temático",
]


def generar_datos_simce(
    db,
    org_id: int,
    user_id: int,
    dims: dict[str, Dimension],
    metrica_est: Metric,
    metrica_preg: Metric,
    nomina: list[dict],
    rnd: random.Random,
) -> tuple[int, int]:
    """Inserta las filas de SIMCE Demo. Devuelve (filas_est, filas_preg)."""
    dificultad = _dificultades(rnd)
    # Pregunta → (habilidad, eje, letra correcta). Estable entre pruebas.
    # Habilidad cicla cada 1 y eje cada 3 a propósito: si ambos usaran el
    # mismo índice quedarían 1-a-1 y los gráficos "por habilidad" y "por eje"
    # serían el mismo gráfico con otras etiquetas.
    perfil_pregunta = [
        (
            HABILIDADES[i % len(HABILIDADES)],
            EJES_SIMCE[(i // len(HABILIDADES)) % len(EJES_SIMCE)],
            LETRAS[(i * 3) % len(LETRAS)],
        )
        for i in range(N_PREGUNTAS)
    ]

    filas_est = 0
    filas_preg = 0
    for k, (anio, mes, n_prueba) in enumerate(EVALUACIONES_SIMCE):
        for est in nomina:
            # Rendimiento continuo: aptitud + efecto curso + mejora + ruido.
            # La dispersión (0.17) se eligió para que los TRES niveles de logro
            # sigan presentes en la última evaluación, no solo en la primera.
            rend = _acotar(
                0.48 + 0.17 * est["aptitud"] + est["offset"] + 0.028 * k
                + rnd.gauss(0, 0.05),
                0.12, 0.97,
            )
            puntaje_simce = int(round(230 + 130 * rend))
            nivel = _nivel_simce(puntaje_simce)

            dims_comunes = {
                "Año": anio,
                "Curso": est["curso"],
                "Nivel": NIVEL_SIMCE,
                "Asignatura": ASIGNATURA_SIMCE,
                "Mes": mes,
                "N Prueba": n_prueba,
            }

            # ── Preguntas del estudiante (1 fila por pregunta) ──
            buenas = 0
            for i, (habilidad, eje, correcta) in enumerate(perfil_pregunta):
                probabilidad = _acotar(rend + dificultad[i], 0.05, 0.97)
                acierta = rnd.random() < probabilidad
                if acierta:
                    buenas += 1
                    respuesta = correcta
                else:
                    otras = [ltr for ltr in LETRAS if ltr != correcta]
                    respuesta = otras[i % len(otras)]
                db.add(
                    _fila(
                        metrica_preg,
                        {
                            "Correcta": correcta,
                            "Respuesta": respuesta,
                            "Correcto": 1 if acierta else 0,
                            "Logro": 1.0 if acierta else 0.0,
                        },
                        {
                            **dims_comunes,
                            "Nombre": est["nombre"],
                            "RUT": est["rut"],
                            "Pregunta": f"P{i + 1}",
                            "Habilidad": habilidad,
                            "Eje Temático": eje,
                        },
                        dims,
                        org_id,
                        user_id,
                    )
                )
                filas_preg += 1

            incorrectas = N_PREGUNTAS - buenas
            omitidas = 1 if incorrectas >= 1 and rnd.random() < 0.15 else 0

            db.add(
                _fila(
                    metrica_est,
                    {
                        "Buenas": buenas,
                        "Malas": incorrectas - omitidas,
                        "Omitidas": omitidas,
                        "Rend": round(rend, 4),
                        "SIMCE": puntaje_simce,
                        "Nota": round(1 + 6 * rend, 1),
                        "Logro": nivel,
                        "Puntaje": buenas,
                    },
                    {
                        **dims_comunes,
                        "Nombre": est["nombre"],
                        "Nombre_Norm": est["nombre_norm"],
                        "RUT": est["rut"],
                        "Nivel de Logro": nivel,
                    },
                    dims,
                    org_id,
                    user_id,
                )
            )
            filas_est += 1

    db.flush()
    return filas_est, filas_preg


# ═════════════════════════════════════════════════════════════════════════
# Datos DIA
# ═════════════════════════════════════════════════════════════════════════

CAMPOS_DIA_ESTUDIANTES = [
    {"name": "Numero Lista", "type": "int"},
    {"name": "Logro", "type": "float"},
    {"name": "Nivel Logro", "type": "str"},
    {"name": "Logro Promedio", "type": "float"},
]

CAMPOS_DIA_PREGUNTAS = [
    {"name": "Logro", "type": "float"},
    {"name": "Nivel Logro", "type": "str"},
]

DIMS_DIA_ESTUDIANTES = [
    "Año", "Curso", "Nivel", "Asignatura", "Hito", "Nombre", "Nombre_Norm",
]

DIMS_DIA_PREGUNTAS = [
    "Año", "Curso", "Nivel", "Asignatura", "Hito",
    "N Pregunta", "Habilidad", "Eje Temático",
]


def generar_datos_dia(
    db,
    org_id: int,
    user_id: int,
    dims: dict[str, Dimension],
    metrica_est: Metric,
    metrica_preg: Metric,
    nomina: list[dict],
    rnd: random.Random,
) -> tuple[int, int, int, int]:
    """Inserta las filas de DIA Demo.

    Devuelve (filas_est, filas_preg, filas_sin_nombre, filas_sin_eje).
    """
    dificultad = _dificultades(rnd)
    # Igual que en SIMCE: habilidad y eje ciclan a distinto paso para que no
    # queden 1-a-1 (ver comentario en generar_datos_simce).
    perfil_pregunta = [
        (
            HABILIDADES[i % len(HABILIDADES)],
            EJES_DIA[(i // len(HABILIDADES)) % len(EJES_DIA)],
        )
        for i in range(N_PREGUNTAS)
    ]

    indice_base = nomina[0]["indice"] - 1
    sin_nombre = {indice_base + i for i in ESTUDIANTES_DIA_SIN_NOMBRE}

    filas_est = 0
    filas_preg = 0
    filas_sin_nombre = 0
    filas_sin_eje = 0

    for k, (anio, hito) in enumerate(EVALUACIONES_DIA):
        # Logro por estudiante primero: el promedio del curso alimenta las
        # filas agregadas de preguntas, para que ambas métricas cuadren.
        logros: dict[int, float] = {}
        for est in nomina:
            logros[est["indice"]] = _acotar(
                0.48 + 0.14 * est["aptitud"] + est["offset"] + 0.055 * k
                + rnd.gauss(0, 0.04),
                0.08, 0.98,
            )

        promedio_curso = {
            curso: sum(logros[e["indice"]] for e in nomina if e["curso"] == curso)
            / max(1, sum(1 for e in nomina if e["curso"] == curso))
            for curso in CURSOS_DIA
        }

        for numero_lista, est in enumerate(nomina, start=1):
            logro = logros[est["indice"]]
            nombre = None if est["indice"] in sin_nombre else est["nombre"]
            if nombre is None:
                filas_sin_nombre += 1
            db.add(
                _fila(
                    metrica_est,
                    {
                        "Numero Lista": (numero_lista - 1) % ESTUDIANTES_POR_CURSO + 1,
                        "Logro": round(logro, 4),
                        "Nivel Logro": _nivel_dia(logro),
                        "Logro Promedio": round(promedio_curso[est["curso"]], 4),
                    },
                    {
                        "Año": anio,
                        "Curso": est["curso"],
                        "Nivel": NIVEL_DIA,
                        "Asignatura": ASIGNATURA_DIA,
                        "Hito": hito,
                        "Nombre": nombre,
                        "Nombre_Norm": est["nombre_norm"],
                    },
                    dims,
                    org_id,
                    user_id,
                )
            )
            filas_est += 1

        # ── Preguntas: agregado por curso × pregunta × hito ──
        for curso in CURSOS_DIA:
            for i, (habilidad, eje) in enumerate(perfil_pregunta):
                logro_preg = _acotar(
                    promedio_curso[curso] + dificultad[i] + rnd.gauss(0, 0.04), 0.03, 0.99
                )
                eje_valor: str | None = eje
                if rnd.random() < PROB_EJE_NULO_DIA:
                    eje_valor = None
                    filas_sin_eje += 1
                db.add(
                    _fila(
                        metrica_preg,
                        {
                            "Logro": round(logro_preg, 4),
                            "Nivel Logro": _nivel_dia(logro_preg),
                        },
                        {
                            "Año": anio,
                            "Curso": curso,
                            "Nivel": NIVEL_DIA,
                            "Asignatura": ASIGNATURA_DIA,
                            "Hito": hito,
                            "N Pregunta": str(i + 1),
                            "Habilidad": habilidad,
                            "Eje Temático": eje_valor,
                        },
                        dims,
                        org_id,
                        user_id,
                    )
                )
                filas_preg += 1

    db.flush()
    return filas_est, filas_preg, filas_sin_nombre, filas_sin_eje


# ═════════════════════════════════════════════════════════════════════════
# Indicadores
# ═════════════════════════════════════════════════════════════════════════

def _branding(lineas_header: list[str]) -> dict:
    """Branding neutro: sin logos, sin firma personal, pie = nombre de la org.

    `left_footer` vacío hace que el template caiga al nombre de la
    organización ("Colegio Demo") — ver report_base.html, div .fb-left.
    """
    return {
        "left_image_id": None,
        "right_image_id": None,
        "center_header": lineas_header,
        "left_footer": "",
        "show_page_number": True,
    }


def crear_indicador_simce(
    db, org_id: int, dims: dict[str, Dimension], metrica_est: Metric, metrica_preg: Metric
) -> Indicator:
    id_est = metrica_est.id_metric
    id_preg = metrica_preg.id_metric

    indicador = Indicator(
        name="SIMCE Demo Lenguaje",
        description=(
            "Indicador sandbox que replica la estructura del SIMCE de Lenguaje: "
            "una métrica por estudiante y otra por pregunta, con evolución "
            "mensual 2025–2026."
        ),
        type="Evaluación",
        column_roles=_volcar(
            {
                "logro_1": [
                    {"metric_id": id_est, "column": "Rend"},
                    {"metric_id": id_preg, "column": "Logro"},
                ],
                "logro_2": [{"metric_id": id_est, "column": "SIMCE"}],
                "nivel_de_logro": [{"metric_id": id_est, "column": "Logro"}],
                "habilidad": [{"metric_id": id_preg, "column": "Habilidad"}],
                "habilidad_2": [{"metric_id": id_preg, "column": "Eje Temático"}],
                "evaluacion_num": [
                    {"metric_id": id_est, "column": "Mes"},
                    {"metric_id": id_preg, "column": "Mes"},
                    {"metric_id": id_est, "column": "Año"},
                    {"metric_id": id_preg, "column": "Año"},
                ],
            }
        ),
        role_labels=_volcar({"logro_1": "Logro", "logro_2": "SIMCE"}),
        role_formats=_volcar({"logro_1": "percent", "logro_2": "#.0"}),
        filter_dimensions=_volcar(
            [
                dims["Año"].id_dimension,
                dims["Curso"].id_dimension,
                dims["Asignatura"].id_dimension,
                dims["Mes"].id_dimension,
                dims["Nivel de Logro"].id_dimension,
            ]
        ),
        temporal_config=_volcar(
            {
                "levels": [
                    {"label": "Año", "sort_mode": "numeric", "order": []},
                    {
                        "label": "Mes",
                        "sort_mode": "custom",
                        "order": ["ABRIL", "JULIO", "NOVIEMBRE"],
                    },
                ]
            }
        ),
        achievement_levels=_volcar(
            [
                {"name": nombre, "color": color, "order": i + 1}
                for i, (nombre, color) in enumerate(zip(NIVELES_SIMCE, COLORES_SEMAFORO))
            ]
        ),
        derived_columns=_volcar(
            [
                {
                    "metric_id": id_est,
                    "temporal_dim_ids": [
                        dims["Mes"].id_dimension,
                        dims["N Prueba"].id_dimension,
                    ],
                    "configs": [
                        {
                            "kind": "agg",
                            "name": "Logro_Promedio_Estudiante",
                            "value_field": "Rend",
                            "entity_field": ["RUT", "Asignatura"],
                            "agg": "mean",
                            "min_points": 1,
                            "on_missing_entity": "null",
                        },
                        {
                            "kind": "slope",
                            "name": "Avance",
                            "value_field": "Rend",
                            "entity_field": ["RUT", "Asignatura", "Año"],
                            "time_field": "Mes",
                            "time_type": "ordinal",
                            "time_ordinal_levels": ["ABRIL", "JULIO", "NOVIEMBRE"],
                            "min_points": 2,
                            "on_missing_entity": "null",
                        },
                        {
                            "kind": "delta",
                            "name": "Mejora_vs_Inicio",
                            "value_field": "Rend",
                            "entity_field": ["RUT", "Asignatura", "Año"],
                            "time_field": "Mes",
                            "time_type": "ordinal",
                            "time_ordinal_levels": ["ABRIL", "JULIO", "NOVIEMBRE"],
                            "min_points": 2,
                            "on_missing_entity": "null",
                        },
                    ],
                }
            ]
        ),
        pdf_layout=_volcar(
            {
                "engine": "weasyprint",
                "mode": "evaluacion",
                "title": "Informe SIMCE Demo — Por evaluación",
                "subtitle": "Resumen de la prueba seleccionada",
                "branding": _branding([NOMBRE_DEMO, "Informe de demostración"]),
                "sections": [
                    {
                        "type": "table",
                        "heading": "Cuadro Resumen Logro por Curso",
                        "item": {
                            "component": "SummaryTable",
                            "valueField": "_logro_1",
                            "groupField": "_curso",
                            "comparePrevious": True,
                        },
                    },
                    {
                        "type": "chart",
                        "heading": "Logro Promedio por Curso",
                        "item": {
                            "component": "BarByGroup",
                            "valueField": "_logro_1",
                            "groupField": "_curso",
                            "showValues": True,
                        },
                    },
                    {
                        "type": "chart",
                        "heading": "Cantidad de Alumnos por Nivel de Logro",
                        "item": {
                            "component": "StackedCountByGroup",
                            "groupField": "_curso",
                            "levelField": "_nivel_de_logro",
                        },
                    },
                    {
                        "type": "chart",
                        "heading": "Logro Promedio por Habilidad",
                        "item": {
                            "component": "BarByGroup",
                            "valueField": "_logro",
                            "groupField": "_habilidad",
                        },
                    },
                    {
                        "type": "chart",
                        "heading": "Logro Promedio por Eje Temático",
                        "item": {
                            "component": "BarByGroup",
                            "valueField": "_logro",
                            "groupField": "_eje_tematico",
                        },
                    },
                ],
            }
        ),
        pdf_layout_historico=_volcar(
            {
                "engine": "weasyprint",
                "mode": "historico",
                "title": "Informe SIMCE Demo — Histórico",
                "subtitle": "Evolución del rendimiento entre evaluaciones",
                "branding": _branding([NOMBRE_DEMO, "Informe de demostración"]),
                "sections": [
                    {
                        "type": "chart",
                        "heading": "Evolución del Logro Promedio por Curso y Mes",
                        "item": {
                            "component": "GroupedBarByPeriod",
                            "valueField": "_logro_1",
                            "groupField": "_curso",
                            "periodField": "_mes",
                        },
                    },
                    {
                        "type": "chart",
                        "heading": "Evolución del Puntaje SIMCE por Curso y Mes",
                        "item": {
                            "component": "GroupedBarByPeriod",
                            "valueField": "_logro_2",
                            "groupField": "_curso",
                            "periodField": "_mes",
                        },
                    },
                    {
                        "type": "chart",
                        "heading": "Evolución de Alumnos por Nivel de Logro",
                        "item": {
                            "component": "StackedCountByGroup",
                            "groupField": "_mes",
                            "levelField": "_nivel_de_logro",
                        },
                    },
                ],
            }
        ),
        dashboard_layout="{}",  # se completa al crear los specs
        report_engine_type="simce",
        org_id=org_id,
    )
    db.add(indicador)
    db.flush()
    for id_metrica in (id_est, id_preg):
        db.add(
            IndicatorMetric(
                id_indicator=indicador.id_indicator, id_metric=id_metrica
            )
        )
    db.flush()
    return indicador


def crear_indicador_dia(
    db, org_id: int, dims: dict[str, Dimension], metrica_est: Metric, metrica_preg: Metric
) -> Indicator:
    id_est = metrica_est.id_metric
    id_preg = metrica_preg.id_metric

    indicador = Indicator(
        name="DIA Demo Lectura",
        description=(
            "Indicador sandbox que replica la estructura del DIA de Lectura: "
            "hitos DIAGNOSTICO / INTERMEDIO / CIERRE, con casos borde "
            "(Eje Temático nulo, Nombre nulo con Nombre_Norm poblado)."
        ),
        type="Evaluación",
        column_roles=_volcar(
            {
                "logro_1": [
                    {"metric_id": id_est, "column": "Logro"},
                    {"metric_id": id_preg, "column": "Logro"},
                ],
                "nivel_de_logro": [
                    {"metric_id": id_est, "column": "Nivel Logro"},
                    {"metric_id": id_preg, "column": "Nivel Logro"},
                ],
                "habilidad": [{"metric_id": id_preg, "column": "Habilidad"}],
                "habilidad_2": [{"metric_id": id_preg, "column": "Eje Temático"}],
                "evaluacion_num": [
                    {"metric_id": id_est, "column": "Hito"},
                    {"metric_id": id_preg, "column": "Hito"},
                    {"metric_id": id_est, "column": "Año"},
                    {"metric_id": id_preg, "column": "Año"},
                ],
            }
        ),
        role_labels=_volcar({"logro_1": "Logro", "logro_2": ""}),
        role_formats=_volcar({"logro_1": "percent"}),
        filter_dimensions=_volcar(
            [
                dims["Año"].id_dimension,
                dims["Curso"].id_dimension,
                dims["Asignatura"].id_dimension,
                dims["Hito"].id_dimension,
                dims["Nivel"].id_dimension,
            ]
        ),
        temporal_config=_volcar(
            {
                "levels": [
                    {"label": "Año", "sort_mode": "numeric", "order": []},
                    {
                        "label": "Hito",
                        "sort_mode": "custom",
                        "order": ["DIAGNOSTICO", "INTERMEDIO", "CIERRE"],
                    },
                ]
            }
        ),
        achievement_levels=_volcar(
            [
                {"name": nombre, "color": color, "order": i + 1}
                for i, (nombre, color) in enumerate(zip(NIVELES_DIA, COLORES_SEMAFORO))
            ]
        ),
        # entity_field usa Nombre_Norm (no Nombre): las filas con Nombre nulo
        # deben conservar sus campos derivados. Ver commit 7527f0a.
        derived_columns=_volcar(
            [
                {
                    "metric_id": id_est,
                    "temporal_dim_ids": [dims["Hito"].id_dimension],
                    "configs": [
                        {
                            "kind": "slope",
                            "name": "Avance",
                            "value_field": "Logro",
                            "entity_field": ["Nombre_Norm", "Asignatura", "Año"],
                            "time_field": "Hito",
                            "time_type": "ordinal",
                            "time_ordinal_levels": [
                                "DIAGNOSTICO",
                                "INTERMEDIO",
                                "CIERRE",
                            ],
                            "min_points": 2,
                            "on_missing_entity": "null",
                        },
                        {
                            "kind": "delta",
                            "name": "Mejora_vs_Inicio",
                            "value_field": "Logro",
                            "entity_field": ["Nombre_Norm", "Asignatura", "Año"],
                            "time_field": "Hito",
                            "time_type": "ordinal",
                            "time_ordinal_levels": [
                                "DIAGNOSTICO",
                                "INTERMEDIO",
                                "CIERRE",
                            ],
                            "min_points": 2,
                            "on_missing_entity": "null",
                        },
                    ],
                }
            ]
        ),
        pdf_layout=_volcar(
            {
                "engine": "weasyprint",
                "mode": "evaluacion",
                "title": "Informe DIA Demo — Por evaluación",
                "subtitle": "Resumen del hito seleccionado",
                "branding": _branding([NOMBRE_DEMO, "Informe de demostración"]),
                "sections": [
                    {
                        "type": "table",
                        "heading": "Cuadro Resumen Logro por Curso",
                        "item": {
                            "component": "SummaryTable",
                            "valueField": "_logro_1",
                            "groupField": "_curso",
                            "comparePrevious": True,
                            "periodField": "_hito",
                        },
                    },
                    {
                        "type": "chart",
                        "heading": "Logro Promedio por Curso",
                        "item": {
                            "component": "BarByGroup",
                            "valueField": "_logro_1",
                            "groupField": "_curso",
                            "showValues": True,
                        },
                    },
                    {
                        "type": "chart",
                        "heading": "Cantidad de Alumnos por Nivel de Logro",
                        "item": {
                            "component": "StackedCountByGroup",
                            "groupField": "_curso",
                            "levelField": "_nivel_de_logro",
                        },
                    },
                    {
                        "type": "chart",
                        "heading": "Logro Promedio por Eje Temático",
                        "item": {
                            "component": "BarByGroup",
                            "valueField": "_logro_1",
                            "groupField": "_eje_tematico",
                        },
                    },
                    {
                        "type": "chart",
                        "heading": "Logro Promedio por Habilidad",
                        "item": {
                            "component": "BarByGroup",
                            "valueField": "_logro_1",
                            "groupField": "_habilidad",
                        },
                    },
                ],
            }
        ),
        pdf_layout_historico=_volcar(
            {
                "engine": "weasyprint",
                "mode": "historico",
                "title": "Informe DIA Demo — Histórico",
                "subtitle": "Evolución entre hitos",
                "branding": _branding([NOMBRE_DEMO, "Informe de demostración"]),
                "sections": [
                    {
                        "type": "chart",
                        "heading": "Evolución del Logro Promedio por Curso y Hito",
                        "item": {
                            "component": "GroupedBarByPeriod",
                            "valueField": "_logro_1",
                            "groupField": "_curso",
                            "periodField": "_hito",
                        },
                    },
                    {
                        "type": "chart",
                        "heading": "Evolución de Alumnos por Nivel de Logro",
                        "item": {
                            "component": "StackedCountByGroup",
                            "groupField": "_hito",
                            "levelField": "_nivel_de_logro",
                        },
                    },
                ],
            }
        ),
        dashboard_layout="{}",
        report_engine_type="dia",
        org_id=org_id,
    )
    db.add(indicador)
    db.flush()
    for id_metrica in (id_est, id_preg):
        db.add(
            IndicatorMetric(id_indicator=indicador.id_indicator, id_metric=id_metrica)
        )
    db.flush()
    return indicador


# ═════════════════════════════════════════════════════════════════════════
# Catálogo de gráficos y tablas (Specs propios de la org demo)
# ═════════════════════════════════════════════════════════════════════════

def _crear_spec(
    db, org_id: int, nombre: str, descripcion: str, tipo: str, config: dict
) -> Spec:
    spec = Spec(
        name=nombre,
        type=tipo,
        metadata_=_meta(descripcion),
        charts_list=_volcar([config]) if tipo == "Gráficos" else "[]",
        tables_list=_volcar([config]) if tipo == "Tablas" else "[]",
        org_id=org_id,
    )
    db.add(spec)
    db.flush()
    return spec


def _grafico(
    tipo_chart: str, metric_id: int, mapeo: dict, estetica: dict
) -> dict:
    """ChartConfig completo (ver backend/schemas_chart.py)."""
    mapping = {
        "x_field": None,
        "y_field": None,
        "group_field": None,
        "stack_field": None,
        "category_field": None,
        "axis_field": None,
        "aggregation": "mean",
    }
    mapping.update(mapeo)
    aesthetics = {
        "titulo": None,
        "x_label": None,
        "y_label": None,
        "y_format": "number",
        "y_lims": None,
        "color_palette": None,
        "palette_reversed": False,
        "show_legend": True,
        "show_values": False,
        "legend_title": None,
        "stack_order": None,
        "x_order": None,
        "bins": 10,
    }
    aesthetics.update(estetica)
    return {
        "version": 1,
        "chart_type": tipo_chart,
        "data_source": {"metric_id": metric_id, "filters": {}, "derived_fields_override": []},
        "mapping": mapping,
        "aesthetics": aesthetics,
    }


def _tabla(metric_id: int, columnas: list[dict], comportamiento: dict) -> dict:
    return {
        "version": 1,
        "data_source": {"metric_id": metric_id, "filters": {}, "derived_fields_override": []},
        "columns": columnas,
        "behavior": comportamiento,
    }


def crear_specs_simce(
    db, org_id: int, indicador: Indicator, id_est: int, id_preg: int
) -> dict[str, int]:
    """Catálogo de tablas/gráficos de SIMCE Demo. Devuelve {clave: id_spec}."""
    ids: dict[str, int] = {}

    ids["tabla_resumen"] = _crear_spec(
        db, org_id, "SIMCE Demo — Resumen por Curso",
        "N° de estudiantes, rendimiento promedio y rangos por curso.", "Tablas",
        _tabla(
            id_est,
            [
                {"key": "Curso", "header": "Curso", "format": "text", "pinned": True},
                {"key": "N", "source_key": "Rend", "header": "N°", "format": "int",
                 "decimals": 0, "agg": "count"},
                {"key": "Rend_mean", "source_key": "Rend", "header": "Rend Promedio",
                 "format": "percent", "decimals": 1, "agg": "mean",
                 "color_scale": ESCALA_DIVERGENTE},
                {"key": "Rend_min", "source_key": "Rend", "header": "Rend Mín",
                 "format": "percent", "decimals": 1, "agg": "min"},
                {"key": "Rend_max", "source_key": "Rend", "header": "Rend Máx",
                 "format": "percent", "decimals": 1, "agg": "max"},
                {"key": "SIMCE_mean", "source_key": "SIMCE", "header": "SIMCE Estimado",
                 "format": "int", "decimals": 0, "agg": "mean"},
            ],
            {
                "pagination": {"enabled": True, "page_size": 50},
                "export": {"csv": True, "xlsx": True},
                "search": False,
                "sorting": [{"column": "Curso", "dir": "asc"}],
                "grouping": {"by": "Curso"},
            },
        ),
    ).id_spec

    ids["tabla_alumnos"] = _crear_spec(
        db, org_id, "SIMCE Demo — Logro por Alumno",
        "Detalle nominal por estudiante con Rend, SIMCE, Nivel y Avance.", "Tablas",
        _tabla(
            id_est,
            [
                {"key": "Nombre", "header": "Estudiante", "format": "text", "pinned": True},
                {"key": "Curso", "header": "Curso", "format": "text"},
                {"key": "Mes", "header": "Mes", "format": "text"},
                {"key": "Rend", "header": "Rendimiento", "format": "percent",
                 "decimals": 1, "color_scale": ESCALA_DIVERGENTE},
                {"key": "SIMCE", "header": "SIMCE", "format": "int", "decimals": 0},
                {"key": "Logro", "header": "Nivel", "format": "text",
                 "color_scale": {
                     "kind": "linked_indicator",
                     "indicator_id": indicador.id_indicator,
                     "level_field": "Logro",
                 }},
                {"key": "Avance", "header": "Avance", "format": "percent",
                 "decimals": 1, "color_scale": ESCALA_DIVERGENTE},
            ],
            {
                "pagination": {"enabled": True, "page_size": 50},
                "export": {"csv": True, "xlsx": True},
                "search": True,
                "sorting": [{"column": "Curso", "dir": "asc"},
                            {"column": "Nombre", "dir": "asc"}],
            },
        ),
    ).id_spec

    ids["tabla_preguntas"] = _crear_spec(
        db, org_id, "SIMCE Demo — Logro por Pregunta",
        "% de acierto por pregunta, con habilidad y eje temático.", "Tablas",
        _tabla(
            id_preg,
            [
                {"key": "Pregunta", "header": "Pregunta", "format": "text", "pinned": True},
                {"key": "Habilidad", "header": "Habilidad", "format": "text"},
                {"key": "Eje Temático", "header": "Eje", "format": "text"},
                {"key": "Curso", "header": "Curso", "format": "text"},
                {"key": "Mes", "header": "Mes", "format": "text"},
                {"key": "Logro", "header": "% Acierto", "format": "percent",
                 "decimals": 1, "agg": "mean", "color_scale": ESCALA_DIVERGENTE},
            ],
            {
                "pagination": {"enabled": True, "page_size": 80},
                "export": {"csv": True, "xlsx": True},
                "search": True,
                "sorting": [{"column": "Curso", "dir": "asc"},
                            {"column": "Pregunta", "dir": "asc"}],
                "grouping": {"by": "Pregunta"},
            },
        ),
    ).id_spec

    ids["chart_rend_curso"] = _crear_spec(
        db, org_id, "SIMCE Demo — Rendimiento por Curso",
        "Promedio de rendimiento (Rend) por curso.", "Gráficos",
        _grafico("bar", id_est,
                 {"x_field": "Curso", "y_field": "Rend"},
                 {"titulo": "Rendimiento Promedio por Curso", "y_label": "Rendimiento",
                  "y_format": "percent", "y_lims": [0, 1], "show_values": True}),
    ).id_spec

    ids["chart_dist_curso"] = _crear_spec(
        db, org_id, "SIMCE Demo — Distribución de Rendimiento por Curso",
        "Boxplot del rendimiento por curso.", "Gráficos",
        _grafico("box", id_est,
                 {"x_field": "Curso", "y_field": "Rend"},
                 {"titulo": "Distribución de Rendimiento", "y_label": "Rendimiento",
                  "y_format": "percent", "y_lims": [0, 1]}),
    ).id_spec

    ids["chart_composicion"] = _crear_spec(
        db, org_id, "SIMCE Demo — Composición por Nivel",
        "Torta con la composición global de niveles de logro.", "Gráficos",
        _grafico("pie", id_est,
                 {"category_field": "Logro"},
                 {"titulo": "Composición por Nivel",
                  "color_overrides": dict(zip(NIVELES_SIMCE, COLORES_SEMAFORO)),
                  "legend_title": "Nivel"}),
    ).id_spec

    ids["chart_niveles_curso"] = _crear_spec(
        db, org_id, "SIMCE Demo — Cantidad por Nivel y Curso",
        "Barras apiladas: distribución de niveles por curso.", "Gráficos",
        _grafico("stacked_bar", id_est,
                 {"x_field": "Curso", "stack_field": "Logro"},
                 {"titulo": "Niveles por Curso", "y_label": "N° Estudiantes",
                  "legend_title": "Nivel", "stack_order": list(NIVELES_SIMCE),
                  "color_overrides": dict(zip(NIVELES_SIMCE, COLORES_SEMAFORO))}),
    ).id_spec

    ids["chart_habilidad"] = _crear_spec(
        db, org_id, "SIMCE Demo — Logro por Habilidad",
        "% de acierto por habilidad, una serie por curso.", "Gráficos",
        _grafico("grouped_bar", id_preg,
                 {"x_field": "Habilidad", "y_field": "Logro", "group_field": "Curso"},
                 {"titulo": "Logro por Habilidad", "y_label": "% Acierto",
                  "y_format": "percent", "y_lims": [0, 1]}),
    ).id_spec

    ids["chart_eje"] = _crear_spec(
        db, org_id, "SIMCE Demo — Logro por Eje Temático",
        "% de acierto por eje temático, una serie por curso.", "Gráficos",
        _grafico("grouped_bar", id_preg,
                 {"x_field": "Eje Temático", "y_field": "Logro", "group_field": "Curso"},
                 {"titulo": "Logro por Eje Temático", "y_label": "% Acierto",
                  "y_format": "percent", "y_lims": [0, 1]}),
    ).id_spec

    ids["chart_heatmap"] = _crear_spec(
        db, org_id, "SIMCE Demo — Heatmap Curso × Eje Temático",
        "Matriz de calor del % de acierto por curso y eje.", "Gráficos",
        _grafico("heatmap", id_preg,
                 {"x_field": "Eje Temático", "y_field": "Logro", "group_field": "Curso"},
                 {"titulo": "Heatmap Curso × Eje Temático", "y_format": "percent",
                  "color_palette": "rojo_calor", "palette_reversed": True}),
    ).id_spec

    ids["chart_evolucion_rend"] = _crear_spec(
        db, org_id, "SIMCE Demo — Evolución Logro Promedio por Curso y Mes",
        "Barras agrupadas: rendimiento promedio por curso, una serie por mes.",
        "Gráficos",
        _grafico("grouped_bar", id_est,
                 {"x_field": "Curso", "y_field": "Rend", "group_field": "Mes"},
                 {"titulo": "Evolución del Logro Promedio por Curso y Mes",
                  "y_label": "Rendimiento", "y_format": "percent", "y_lims": [0, 1],
                  "show_values": True,
                  "stack_order": ["ABRIL", "JULIO", "NOVIEMBRE"]}),
    ).id_spec

    ids["chart_evolucion_simce"] = _crear_spec(
        db, org_id, "SIMCE Demo — Evolución del SIMCE Promedio por Curso y Mes",
        "Barras agrupadas: puntaje SIMCE promedio por curso, una serie por mes.",
        "Gráficos",
        _grafico("grouped_bar", id_est,
                 {"x_field": "Curso", "y_field": "SIMCE", "group_field": "Mes"},
                 {"titulo": "Evolución del SIMCE Promedio por Curso y Mes",
                  "y_label": "Puntaje SIMCE", "y_format": "int",
                  "stack_order": ["ABRIL", "JULIO", "NOVIEMBRE"]}),
    ).id_spec

    ids["chart_tendencia"] = _crear_spec(
        db, org_id, "SIMCE Demo — Tendencia de Rendimiento por Mes",
        "Línea de rendimiento promedio por mes, una serie por curso.", "Gráficos",
        _grafico("line", id_est,
                 {"x_field": "Mes", "y_field": "Rend", "group_field": "Curso"},
                 {"titulo": "Tendencia de Rendimiento por Mes", "x_label": "Mes",
                  "y_label": "Rendimiento", "y_format": "percent", "y_lims": [0, 1],
                  "x_order": ["ABRIL", "JULIO", "NOVIEMBRE"]}),
    ).id_spec

    return ids


def crear_specs_dia(
    db, org_id: int, indicador: Indicator, id_est: int, id_preg: int
) -> dict[str, int]:
    """Catálogo de tablas/gráficos de DIA Demo. Devuelve {clave: id_spec}."""
    ids: dict[str, int] = {}

    ids["tabla_resumen"] = _crear_spec(
        db, org_id, "DIA Demo — Resumen por Curso",
        "N° de alumnos, logro promedio y dispersión por curso.", "Tablas",
        _tabla(
            id_est,
            [
                {"key": "Curso", "header": "Curso", "format": "text", "pinned": True},
                {"key": "N_alumnos", "source_key": "Logro", "header": "N° Alumnos",
                 "format": "int", "decimals": 0, "agg": "count"},
                {"key": "Logro_mean", "source_key": "Logro", "header": "Logro Promedio",
                 "format": "percent", "decimals": 1, "agg": "mean",
                 "color_scale": ESCALA_DIVERGENTE},
                {"key": "Logro_min", "source_key": "Logro", "header": "Logro Mín",
                 "format": "percent", "decimals": 1, "agg": "min"},
                {"key": "Logro_max", "source_key": "Logro", "header": "Logro Máx",
                 "format": "percent", "decimals": 1, "agg": "max"},
                {"key": "Logro_std", "source_key": "Logro", "header": "Desviación",
                 "format": "percent", "decimals": 2, "agg": "std"},
            ],
            {
                "pagination": {"enabled": True, "page_size": 50},
                "export": {"csv": True, "xlsx": True},
                "search": False,
                "sorting": [{"column": "Curso", "dir": "asc"}],
                "grouping": {"by": "Curso"},
            },
        ),
    ).id_spec

    ids["tabla_alumnos"] = _crear_spec(
        db, org_id, "DIA Demo — Logro por Alumno",
        "Detalle nominal por estudiante e hito, con nivel y avance.", "Tablas",
        _tabla(
            id_est,
            [
                {"key": "Numero Lista", "header": "N°", "format": "int",
                 "width": 70, "pinned": True},
                {"key": "Nombre", "header": "Estudiante", "format": "text"},
                {"key": "Nombre_Norm", "header": "Clave", "format": "text"},
                {"key": "Curso", "header": "Curso", "format": "text"},
                {"key": "Hito", "header": "Hito", "format": "text"},
                {"key": "Logro", "header": "Logro", "format": "percent",
                 "decimals": 1, "color_scale": ESCALA_DIVERGENTE},
                {"key": "Nivel Logro", "header": "Nivel", "format": "text",
                 "color_scale": {
                     "kind": "linked_indicator",
                     "indicator_id": indicador.id_indicator,
                     "level_field": "Nivel Logro",
                 }},
                {"key": "Avance", "header": "Avance", "format": "percent",
                 "decimals": 1, "color_scale": ESCALA_DIVERGENTE},
            ],
            {
                "pagination": {"enabled": True, "page_size": 50},
                "export": {"csv": True, "xlsx": True},
                "search": True,
                "sorting": [{"column": "Curso", "dir": "asc"},
                            {"column": "Numero Lista", "dir": "asc"}],
            },
        ),
    ).id_spec

    ids["tabla_preguntas"] = _crear_spec(
        db, org_id, "DIA Demo — Logro por Pregunta",
        "% de acierto por pregunta, con habilidad y eje temático.", "Tablas",
        _tabla(
            id_preg,
            [
                {"key": "N Pregunta", "header": "N° Preg.", "format": "int",
                 "width": 80, "pinned": True},
                {"key": "Habilidad", "header": "Habilidad", "format": "text"},
                {"key": "Eje Temático", "header": "Eje", "format": "text"},
                {"key": "Curso", "header": "Curso", "format": "text"},
                {"key": "Hito", "header": "Hito", "format": "text"},
                {"key": "Logro", "header": "% Acierto", "format": "percent",
                 "decimals": 1, "color_scale": ESCALA_DIVERGENTE},
                {"key": "Nivel Logro", "header": "Nivel", "format": "text"},
            ],
            {
                "pagination": {"enabled": True, "page_size": 80},
                "export": {"csv": True, "xlsx": True},
                "search": True,
                "sorting": [{"column": "Curso", "dir": "asc"},
                            {"column": "N Pregunta", "dir": "asc"}],
            },
        ),
    ).id_spec

    ids["chart_logro_curso"] = _crear_spec(
        db, org_id, "DIA Demo — Logro Promedio por Curso",
        "Barras del logro promedio por curso.", "Gráficos",
        _grafico("bar", id_est,
                 {"x_field": "Curso", "y_field": "Logro"},
                 {"titulo": "Logro Promedio por Curso", "y_label": "Logro",
                  "y_format": "percent", "y_lims": [0, 1], "show_values": True}),
    ).id_spec

    ids["chart_dist_curso"] = _crear_spec(
        db, org_id, "DIA Demo — Distribución de Logro por Curso",
        "Boxplot del logro por curso.", "Gráficos",
        _grafico("box", id_est,
                 {"x_field": "Curso", "y_field": "Logro"},
                 {"titulo": "Distribución de Logro por Curso", "y_label": "Logro",
                  "y_format": "percent", "y_lims": [0, 1]}),
    ).id_spec

    ids["chart_niveles_curso"] = _crear_spec(
        db, org_id, "DIA Demo — Cantidad de Alumnos por Nivel de Logro",
        "Barras apiladas: niveles de logro por curso.", "Gráficos",
        _grafico("stacked_bar", id_est,
                 {"x_field": "Curso", "stack_field": "Nivel Logro"},
                 {"titulo": "Niveles de Logro por Curso", "y_label": "N° Alumnos",
                  "legend_title": "Nivel", "stack_order": list(NIVELES_DIA),
                  "color_overrides": dict(zip(NIVELES_DIA, COLORES_SEMAFORO))}),
    ).id_spec

    ids["chart_composicion"] = _crear_spec(
        db, org_id, "DIA Demo — Composición por Nivel de Logro",
        "Torta con la composición global de niveles.", "Gráficos",
        _grafico("pie", id_est,
                 {"category_field": "Nivel Logro"},
                 {"titulo": "Composición por Nivel de Logro",
                  "legend_title": "Nivel",
                  "color_overrides": dict(zip(NIVELES_DIA, COLORES_SEMAFORO))}),
    ).id_spec

    ids["chart_eje"] = _crear_spec(
        db, org_id, "DIA Demo — Logro por Eje Temático",
        "% de acierto por eje temático, una serie por curso.", "Gráficos",
        _grafico("grouped_bar", id_preg,
                 {"x_field": "Eje Temático", "y_field": "Logro", "group_field": "Curso"},
                 {"titulo": "Logro por Eje Temático", "y_label": "Logro",
                  "y_format": "percent", "y_lims": [0, 1]}),
    ).id_spec

    ids["chart_habilidad"] = _crear_spec(
        db, org_id, "DIA Demo — Logro por Habilidad",
        "% de acierto por habilidad, una serie por curso.", "Gráficos",
        _grafico("grouped_bar", id_preg,
                 {"x_field": "Habilidad", "y_field": "Logro", "group_field": "Curso"},
                 {"titulo": "Logro por Habilidad", "y_label": "Logro",
                  "y_format": "percent", "y_lims": [0, 1]}),
    ).id_spec

    ids["chart_heatmap"] = _crear_spec(
        db, org_id, "DIA Demo — Heatmap Curso × Eje Temático",
        "Matriz de calor del logro por curso y eje.", "Gráficos",
        _grafico("heatmap", id_preg,
                 {"x_field": "Eje Temático", "y_field": "Logro", "group_field": "Curso"},
                 {"titulo": "Heatmap Curso × Eje Temático", "y_format": "percent",
                  "color_palette": "rojo_calor", "palette_reversed": True}),
    ).id_spec

    ids["chart_tendencia"] = _crear_spec(
        db, org_id, "DIA Demo — Tendencia de Logro por Hito",
        "Línea del logro promedio por hito, una serie por curso.", "Gráficos",
        _grafico("line", id_est,
                 {"x_field": "Hito", "y_field": "Logro", "group_field": "Curso"},
                 {"titulo": "Tendencia de Logro por Hito", "x_label": "Hito",
                  "y_label": "Logro", "y_format": "percent", "y_lims": [0, 1],
                  "x_order": ["DIAGNOSTICO", "INTERMEDIO", "CIERRE"]}),
    ).id_spec

    return ids


# ═════════════════════════════════════════════════════════════════════════
# Dashboards
# ═════════════════════════════════════════════════════════════════════════

def _fila_dashboard(columnas: int, items: list[dict]) -> dict:
    return {"cols": columnas, "items": items}


def _tabla_dashboard(id_spec: int, titulo: str) -> dict:
    return {"type": "configured_table", "spec_id": id_spec, "title": titulo}


def _chart_dashboard(id_spec: int, titulo: str) -> dict:
    return {"type": "configured_chart", "spec_id": id_spec, "title": titulo}


def dashboard_simce(ids: dict[str, int]) -> dict:
    return {
        "tabs": [
            {
                "id": "general",
                "label": "Vista General",
                "rows": [
                    _fila_dashboard(4, [{"type": "kpis"}]),
                    _fila_dashboard(1, [_tabla_dashboard(ids["tabla_resumen"],
                                                         "Resumen por Curso")]),
                    _fila_dashboard(2, [
                        _chart_dashboard(ids["chart_rend_curso"], "Rendimiento por Curso"),
                        _chart_dashboard(ids["chart_dist_curso"], "Distribución por Curso"),
                    ]),
                    _fila_dashboard(2, [
                        _chart_dashboard(ids["chart_composicion"], "Composición Global"),
                        _chart_dashboard(ids["chart_niveles_curso"], "Niveles por Curso"),
                    ]),
                ],
            },
            {
                "id": "curso",
                "label": "Por Curso",
                "rows": [
                    _fila_dashboard(1, [{"type": "course_selector"}]),
                    _fila_dashboard(2, [
                        _chart_dashboard(ids["chart_habilidad"], "Logro por Habilidad"),
                        _chart_dashboard(ids["chart_eje"], "Logro por Eje"),
                    ]),
                    _fila_dashboard(1, [_chart_dashboard(ids["chart_heatmap"],
                                                         "Heatmap Curso × Eje")]),
                    _fila_dashboard(1, [_tabla_dashboard(ids["tabla_preguntas"],
                                                         "Logro por Pregunta")]),
                ],
            },
            {
                "id": "estudiante",
                "label": "Por Estudiante",
                "rows": [
                    _fila_dashboard(1, [{"type": "course_selector"}]),
                    _fila_dashboard(1, [_tabla_dashboard(ids["tabla_alumnos"],
                                                         "Logro por Alumno")]),
                ],
            },
            {
                "id": "tendencia",
                "label": "Tendencia",
                "rows": [
                    _fila_dashboard(1, [_chart_dashboard(
                        ids["chart_evolucion_rend"],
                        "Evolución Logro Promedio por Curso y Mes")]),
                    _fila_dashboard(1, [_chart_dashboard(
                        ids["chart_evolucion_simce"],
                        "Evolución SIMCE Promedio por Curso y Mes")]),
                    _fila_dashboard(1, [_chart_dashboard(ids["chart_tendencia"],
                                                         "Tendencia por Mes")]),
                ],
            },
        ]
    }


def dashboard_dia(ids: dict[str, int]) -> dict:
    return {
        "tabs": [
            {
                "id": "general",
                "label": "Vista General",
                "rows": [
                    _fila_dashboard(4, [{"type": "kpis"}]),
                    _fila_dashboard(1, [_tabla_dashboard(ids["tabla_resumen"],
                                                         "Resumen por Curso")]),
                    _fila_dashboard(2, [
                        _chart_dashboard(ids["chart_logro_curso"], "Logro por Curso"),
                        _chart_dashboard(ids["chart_dist_curso"], "Distribución por Curso"),
                    ]),
                    _fila_dashboard(2, [
                        _chart_dashboard(ids["chart_composicion"], "Composición Global"),
                        _chart_dashboard(ids["chart_niveles_curso"],
                                         "Niveles de Logro por Curso"),
                    ]),
                ],
            },
            {
                "id": "curso",
                "label": "Por Curso",
                "rows": [
                    _fila_dashboard(1, [{"type": "course_selector"}]),
                    _fila_dashboard(2, [
                        _chart_dashboard(ids["chart_eje"], "Logro por Eje Temático"),
                        _chart_dashboard(ids["chart_habilidad"], "Logro por Habilidad"),
                    ]),
                    _fila_dashboard(1, [_chart_dashboard(ids["chart_heatmap"],
                                                         "Heatmap Curso × Eje")]),
                    _fila_dashboard(1, [_tabla_dashboard(ids["tabla_preguntas"],
                                                         "Logro por Pregunta")]),
                ],
            },
            {
                "id": "estudiante",
                "label": "Por Estudiante",
                "rows": [
                    _fila_dashboard(1, [{"type": "course_selector"}]),
                    _fila_dashboard(1, [_tabla_dashboard(ids["tabla_alumnos"],
                                                         "Logro por Alumno")]),
                ],
            },
            {
                "id": "tendencia",
                "label": "Tendencia",
                "rows": [
                    _fila_dashboard(1, [_chart_dashboard(ids["chart_tendencia"],
                                                         "Tendencia por Hito")]),
                ],
            },
        ]
    }


# ═════════════════════════════════════════════════════════════════════════
# Orquestación
# ═════════════════════════════════════════════════════════════════════════

def construir(db) -> dict:
    """Crea la org demo completa. Devuelve el resumen para imprimir."""
    rnd = random.Random(SEMILLA)

    org, admin = crear_org_y_admin(db)
    org_id = org.id
    dims = crear_dimensiones(db, org_id)

    # ── Métricas ──
    metrica_simce_est = crear_metrica(
        db, org_id, "Resultados SIMCE Demo por Estudiante",
        "Una fila por estudiante y evaluación (demo).",
        CAMPOS_SIMCE_ESTUDIANTES, DIMS_SIMCE_ESTUDIANTES, dims,
    )
    metrica_simce_preg = crear_metrica(
        db, org_id, "Resultados SIMCE Demo por Pregunta",
        "Una fila por estudiante, pregunta y evaluación (demo).",
        CAMPOS_SIMCE_PREGUNTAS, DIMS_SIMCE_PREGUNTAS, dims,
    )
    metrica_dia_est = crear_metrica(
        db, org_id, "Resultados DIA Demo por Estudiante",
        "Una fila por estudiante e hito (demo).",
        CAMPOS_DIA_ESTUDIANTES, DIMS_DIA_ESTUDIANTES, dims,
    )
    metrica_dia_preg = crear_metrica(
        db, org_id, "Resultados DIA Demo por Pregunta",
        "Una fila por curso, pregunta e hito (demo).",
        CAMPOS_DIA_PREGUNTAS, DIMS_DIA_PREGUNTAS, dims,
    )

    # ── Datos ──
    nomina_simce = generar_nomina(CURSOS_SIMCE, 1, rnd)
    nomina_dia = generar_nomina(CURSOS_DIA, len(nomina_simce) + 1, rnd)

    filas_simce_est, filas_simce_preg = generar_datos_simce(
        db, org_id, admin.id, dims, metrica_simce_est, metrica_simce_preg,
        nomina_simce, rnd,
    )
    filas_dia_est, filas_dia_preg, sin_nombre, sin_eje = generar_datos_dia(
        db, org_id, admin.id, dims, metrica_dia_est, metrica_dia_preg,
        nomina_dia, rnd,
    )

    # ── Indicadores ──
    ind_simce = crear_indicador_simce(
        db, org_id, dims, metrica_simce_est, metrica_simce_preg
    )
    ind_dia = crear_indicador_dia(db, org_id, dims, metrica_dia_est, metrica_dia_preg)

    # ── Specs + dashboards (necesitan el id del indicador ya creado) ──
    specs_simce = crear_specs_simce(
        db, org_id, ind_simce, metrica_simce_est.id_metric, metrica_simce_preg.id_metric
    )
    specs_dia = crear_specs_dia(
        db, org_id, ind_dia, metrica_dia_est.id_metric, metrica_dia_preg.id_metric
    )
    ind_simce.dashboard_layout = _volcar(dashboard_simce(specs_simce))
    ind_dia.dashboard_layout = _volcar(dashboard_dia(specs_dia))
    db.flush()

    return {
        "org": {"id": org_id, "name": org.name, "slug": org.slug},
        "admin": {"id": admin.id, "email": admin.email, "role": admin.role},
        "dimensiones": {n: d.id_dimension for n, d in dims.items()},
        "metricas": {
            "SIMCE estudiantes": (metrica_simce_est.id_metric, filas_simce_est),
            "SIMCE preguntas": (metrica_simce_preg.id_metric, filas_simce_preg),
            "DIA estudiantes": (metrica_dia_est.id_metric, filas_dia_est),
            "DIA preguntas": (metrica_dia_preg.id_metric, filas_dia_preg),
        },
        "indicadores": {
            ind_simce.name: ind_simce.id_indicator,
            ind_dia.name: ind_dia.id_indicator,
        },
        "specs": {"SIMCE Demo": specs_simce, "DIA Demo": specs_dia},
        "estudiantes": len(nomina_simce) + len(nomina_dia),
        "casos_borde": {
            "filas DIA con Nombre nulo": sin_nombre,
            "filas DIA con Eje Temático nulo": sin_eje,
        },
    }


def imprimir_resumen(resumen: dict, borrados: dict[str, int] | None) -> None:
    print()
    print("=" * 72)
    print("  ORGANIZACIÓN DEMO CREADA")
    print("=" * 72)

    if borrados:
        print("\n-- Borrado previo (--reset) ------------------------------------")
        for tabla, n in borrados.items():
            print(f"   {tabla:<24} {n:>7}")

    org = resumen["org"]
    admin = resumen["admin"]
    print("\n-- Organización -----------------------------------------------")
    print(f"   id={org['id']}  name='{org['name']}'  slug='{org['slug']}'")
    print("\n-- Usuario admin ----------------------------------------------")
    print(f"   id={admin['id']}  email={admin['email']}  role={admin['role']}")
    print(f"   password={PASSWORD_ADMIN}")

    print("\n-- Dimensiones ------------------------------------------------")
    for nombre, id_dim in resumen["dimensiones"].items():
        print(f"   {id_dim:>4}  {nombre}")

    print("\n-- Métricas (id, filas de metric_data) ------------------------")
    total_filas = 0
    for nombre, (id_metrica, filas) in resumen["metricas"].items():
        total_filas += filas
        print(f"   {id_metrica:>4}  {nombre:<24} {filas:>7} filas")
    print(f"   {'':>4}  {'TOTAL metric_data':<24} {total_filas:>7} filas")

    print("\n-- Indicadores ------------------------------------------------")
    for nombre, id_ind in resumen["indicadores"].items():
        print(f"   {id_ind:>4}  {nombre}")

    print("\n-- Specs (catálogo de gráficos y tablas) ----------------------")
    total_specs = 0
    for grupo, ids in resumen["specs"].items():
        print(f"   {grupo}:")
        for clave, id_spec in ids.items():
            total_specs += 1
            print(f"      {id_spec:>4}  {clave}")
    print(f"   total specs: {total_specs}")

    print("\n-- Otros conteos ----------------------------------------------")
    print(f"   estudiantes sintéticos: {resumen['estudiantes']}")
    for etiqueta, n in resumen["casos_borde"].items():
        print(f"   {etiqueta}: {n}")

    print("\n-- Cómo usarla ------------------------------------------------")
    print(f"   Login: {EMAIL_ADMIN} / {PASSWORD_ADMIN}")
    print("   Todo el contenido vive bajo el org_id de la demo; ninguna otra")
    print("   organización fue leída ni modificada en la escritura.")
    print("=" * 72)
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Crea la organización sandbox 'Colegio Demo' con datos sintéticos."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Si la org demo ya existe, borra TODO lo suyo y la recrea.",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        existente = (
            db.query(Organization).filter(Organization.slug == SLUG_DEMO).first()
        )
        borrados: dict[str, int] | None = None
        if existente:
            if not args.reset:
                print(
                    f"ERROR: la organización '{SLUG_DEMO}' ya existe (id={existente.id}).\n"
                    "       Usa --reset para borrarla y recrearla desde cero."
                )
                return 1
            print(f"--reset: borrando la organización demo existente (id={existente.id})...")
            borrados = borrar_org(db, existente)

        resumen = construir(db)
        db.commit()
        imprimir_resumen(resumen, borrados)
        return 0
    except Exception as exc:  # noqa: BLE001 — script CLI: reportar y salir
        db.rollback()
        print(f"ERROR: falló la creación de la org demo: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
