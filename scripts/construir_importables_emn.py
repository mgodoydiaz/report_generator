# -*- coding: utf-8 -*-
"""
construir_importables_emn.py
============================
Convierte los Excel originales de Aptus (`Informe_logro_por_{estudiante|OA|habilidad} MES.xlsx`)
en 3 archivos xlsx listos para importar por `POST /api/metrics/{id}/import`:

    Importar_metric24_estudiante.xlsx   -> metric 24 "Resultados SIMCE Panguipulli por Estudiante"
    Importar_metric25_oa.xlsx           -> metric 25 "Resultados SIMCE Panguipulli por OA"
    Importar_metric26_habilidad.xlsx    -> metric 26 "Resultados SIMCE Panguipulli por Habilidad"

Replica EXACTAMENTE los mapeos de los specs 49/50/51 y las transformaciones del step
`ModifyColumnValues` del pipeline 26 "SIMCE Panguipulli (Aptus) - Carga directa".

IMPORTANTE — DEDUPLICACION
--------------------------
El arbol de originales guarda el MISMO libro varias veces (una copia por carpeta de
asignatura y de nivel), pero cada libro ya contiene TODOS los niveles y TODAS las
asignaturas del proceso. Un recorrido recursivo ingenuo multiplicaria las filas x2 (2024)
o x4 (2025). Este script deduplica a nivel de CONTENIDO (hash del DataFrame ordenado),
quedandose con un archivo canonico por (tipo, contenido).

Uso
---
    python construir_importables_emn.py
    python construir_importables_emn.py --anio 2025
    python construir_importables_emn.py --anio 2025 --mes SEPTIEMBRE
    python construir_importables_emn.py --origen "D:\\ruta\\Resultados Aptus" --salida "D:\\out"
"""
from __future__ import annotations

import argparse
import hashlib
import io
import sys
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# --------------------------------------------------------------------------------------
# Defaults (descubiertos por glob para no depender de acentos escritos a mano)
# --------------------------------------------------------------------------------------
_BASE_DOCS = Path.home() / "Documents" / "Proyectos"


def _default_origen() -> Path:
    """Localiza la carpeta 'Resultados Aptus' por glob, sin escribir acentos a mano."""
    if _BASE_DOCS.is_dir():
        for cand in sorted(_BASE_DOCS.glob("*/*/*/Resultados Aptus")):
            if cand.is_dir():
                return cand
        for cand in sorted(_BASE_DOCS.glob("**/Resultados Aptus")):
            if cand.is_dir():
                return cand
    return Path.cwd()


def _default_salida() -> Path:
    return Path(__file__).resolve().parent


# --------------------------------------------------------------------------------------
# Especificacion (specs 49/50/51 + ModifyColumnValues del pipeline 26)
# --------------------------------------------------------------------------------------
ESTABLECIMIENTO = "Panguipulli"

MES_A_N_PRUEBA = {"ABRIL": 1, "MAYO": 2, "AGOSTO": 3, "SEPTIEMBRE": 4}

# spec -> {columna origen en el Excel: columna destino}
MAPEOS = {
    "estudiante": {
        "NOMBRE PROCESO": "Proceso_raw",
        "AÑO": "Año",
        "NIVEL": "Nivel",
        "CURSO": "Curso_letra",
        "ASIGNATURA": "Asignatura_raw",
        "RUT": "RUT",
        "APELLIDO PATERNO": "A_P",
        "APELLIDO MATERNO": "A_M",
        "PRIMER NOMBRE": "P_N",
        "SEGUNDO NOMBRE": "S_N",
        "PORCENTAJE LOGRO": "PorcLogro",
        "LOGRO NORMALIZADO": "LogroNormalizado",
    },
    "oa": {
        "NOMBRE PROCESO": "Proceso_raw",
        "AÑO": "Año",
        "NIVEL": "Nivel",
        "CURSO": "Curso_letra",
        "ASIGNATURA": "Asignatura_raw",
        "NÚMERO OA": "N OA",
        "OA": "OA",
        "LOGRO": "Logro",
    },
    "habilidad": {
        "NOMBRE PROCESO": "Proceso_raw",
        "AÑO": "Año",
        "NIVEL": "Nivel",
        "CURSO": "Curso_letra",
        "ASIGNATURA": "Asignatura_raw",
        "PORCENTAJE LOGRO CURSO": "LogroCurso",
        "HABILIDAD": "Habilidad",
        "PORCENTAJE LOGRO HABILIDAD": "LogroHabilidad",
    },
}

# Columnas numericas que en el origen vienen con coma decimal
COLS_NUMERICAS = {
    "estudiante": ["PorcLogro", "LogroNormalizado"],
    "oa": ["Logro"],
    "habilidad": ["LogroCurso", "LogroHabilidad"],
}

# Esquema destino EXACTO (punto C) — orden incluido
COLUMNAS_SALIDA = {
    "estudiante": ["Establecimiento", "Año", "Mes", "N Prueba", "Asignatura", "Nivel",
                   "Curso", "RUT", "Nombre", "PorcLogro", "LogroNormalizado"],
    "oa": ["Establecimiento", "Año", "Mes", "N Prueba", "Asignatura", "Nivel",
           "Curso", "N OA", "OA", "Logro"],
    "habilidad": ["Establecimiento", "Año", "Mes", "N Prueba", "Asignatura", "Nivel",
                  "Curso", "Habilidad", "LogroCurso", "LogroHabilidad"],
}

ARCHIVOS_SALIDA = {
    "estudiante": "Importar_metric24_estudiante.xlsx",
    "oa": "Importar_metric25_oa.xlsx",
    "habilidad": "Importar_metric26_habilidad.xlsx",
}

HOJA_SALIDA = "Datos"


# --------------------------------------------------------------------------------------
# Transformaciones (ModifyColumnValues, identicas a produccion)
# --------------------------------------------------------------------------------------
def derivar_mes(proceso_raw) -> str:
    """'EMN Abril' -> 'ABRIL'; tolera 'EMN agosto' y 'EMN Septiembre ' (espacio final)."""
    return str(proceso_raw).replace("EMN ", "").strip().upper()


def derivar_n_prueba(mes: str) -> int:
    return MES_A_N_PRUEBA.get(mes, 0)


def derivar_asignatura(asignatura_raw) -> str:
    a = str(asignatura_raw)
    if "Lenguaje" in a:
        return "LENGUAJE"
    if "Matem" in a:
        return "MATEMATICA"
    if "Historia" in a:
        return "HISTORIA"
    return a.upper()


def derivar_curso(nivel, curso_letra) -> str:
    return f"{nivel} {curso_letra}"


def derivar_nombre(a_p, a_m, p_n, s_n) -> str:
    partes = [a_p, a_m, p_n, s_n]
    return " ".join(str(x) for x in partes if x is not None and str(x) != "nan" and str(x) != "")


def a_float(v):
    """Coma decimal -> punto decimal, como float nativo. NaN se preserva."""
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return float("nan")


# --------------------------------------------------------------------------------------
# Descubrimiento y deduplicacion
# --------------------------------------------------------------------------------------
def tipo_de_informe(p: Path) -> str | None:
    n = p.name.lower()
    if "por_estudiante" in n:
        return "estudiante"
    if "por_oa" in n:
        return "oa"
    if "por_habilidad" in n:
        return "habilidad"
    return None


def descubrir(origen: Path) -> dict[str, list[Path]]:
    """Recorre recursivamente y agrupa por tipo de informe (glob, sin rutas literales)."""
    out: dict[str, list[Path]] = {"estudiante": [], "oa": [], "habilidad": []}
    for p in sorted(origen.rglob("*.xlsx")):
        if p.name.startswith("~$") or p.name.startswith("._"):
            continue
        if not p.name.lower().startswith("informe_logro_por"):
            continue
        t = tipo_de_informe(p)
        if t:
            out[t].append(p)
    return out


def hash_contenido(df: pd.DataFrame) -> str:
    d = df.fillna("").astype(str)
    return hashlib.md5(d.sort_values(list(d.columns)).to_csv(index=False).encode()).hexdigest()


def canonicos(paths: list[Path]) -> tuple[list[tuple[Path, pd.DataFrame]], list[tuple[Path, Path]]]:
    """Devuelve (canonicos, descartados) deduplicando por contenido del DataFrame."""
    vistos: dict[str, Path] = {}
    keep: list[tuple[Path, pd.DataFrame]] = []
    dropped: list[tuple[Path, Path]] = []
    for p in paths:
        df = pd.read_excel(p, sheet_name=0, header=0, engine="openpyxl", dtype=str)
        h = hash_contenido(df)
        if h in vistos:
            dropped.append((p, vistos[h]))
        else:
            vistos[h] = p
            keep.append((p, df))
    return keep, dropped


# --------------------------------------------------------------------------------------
# Construccion
# --------------------------------------------------------------------------------------
def construir(tipo: str, pares: list[tuple[Path, pd.DataFrame]],
              anio: str | None, mes: str | None) -> pd.DataFrame:
    mapeo = MAPEOS[tipo]
    partes = []

    for p, raw in pares:
        faltan = [c for c in mapeo if c not in raw.columns]
        if faltan:
            print(f"  !! OMITIDO (faltan columnas {faltan}): {p.name}")
            continue

        # 1) mapeo de columnas origen -> destino (ignora columnas extra como RBD/COLEGIO)
        d = raw[list(mapeo.keys())].rename(columns=mapeo).copy()

        # 2) inyeccion de contexto
        d["Establecimiento"] = ESTABLECIMIENTO

        # 3) transformaciones por fila
        d["Mes"] = d["Proceso_raw"].map(derivar_mes)
        d["N Prueba"] = d["Mes"].map(derivar_n_prueba).astype(int)
        d["Asignatura"] = d["Asignatura_raw"].map(derivar_asignatura)
        d["Curso"] = [derivar_curso(n, c) for n, c in zip(d["Nivel"], d["Curso_letra"])]
        if tipo == "estudiante":
            d["Nombre"] = [derivar_nombre(*t) for t in zip(d["A_P"], d["A_M"], d["P_N"], d["S_N"])]

        # 4) coma -> punto decimal, float nativo
        for c in COLS_NUMERICAS[tipo]:
            d[c] = d[c].map(a_float)

        # Año como entero nativo (el export de produccion lo trae int64)
        d["Año"] = pd.to_numeric(d["Año"], errors="coerce").astype("Int64")

        d["_origen"] = str(p)
        partes.append(d)

    if not partes:
        return pd.DataFrame(columns=COLUMNAS_SALIDA[tipo])

    d = pd.concat(partes, ignore_index=True)

    # 5) filtros opcionales
    if anio:
        d = d[d["Año"].astype(str) == str(anio)]
    if mes:
        d = d[d["Mes"] == str(mes).strip().upper()]

    return d.reset_index(drop=True)


def escribir(d: pd.DataFrame, tipo: str, salida: Path) -> Path:
    cols = COLUMNAS_SALIDA[tipo]
    out = d.reindex(columns=cols)          # orden exacto, descarta auxiliares
    out["Año"] = out["Año"].astype("Int64")
    out["N Prueba"] = out["N Prueba"].astype("Int64")
    destino = salida / ARCHIVOS_SALIDA[tipo]
    with pd.ExcelWriter(destino, engine="openpyxl") as w:
        out.to_excel(w, sheet_name=HOJA_SALIDA, index=False, header=True)
    return destino


# --------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Construye los xlsx importables de EMN Aptus.")
    ap.add_argument("--origen", type=Path, default=_default_origen(),
                    help="Carpeta raiz de los originales de Aptus (se recorre recursivamente).")
    ap.add_argument("--salida", type=Path, default=_default_salida(),
                    help="Carpeta donde escribir los 3 xlsx.")
    ap.add_argument("--anio", default=None, help="Filtrar por año, p.ej. 2025.")
    ap.add_argument("--mes", default=None, help="Filtrar por mes derivado, p.ej. SEPTIEMBRE.")
    ap.add_argument("--sin-dedup", action="store_true",
                    help="NO deduplicar por contenido (peligroso: multiplica filas).")
    args = ap.parse_args()

    origen: Path = args.origen.resolve()
    salida: Path = args.salida.resolve()
    salida.mkdir(parents=True, exist_ok=True)

    print("=" * 92)
    print("CONSTRUCTOR DE IMPORTABLES EMN APTUS")
    print("=" * 92)
    print(f"origen : {origen}")
    print(f"salida : {salida}")
    print(f"filtros: anio={args.anio or '(todos)'} mes={args.mes or '(todos)'}")
    if not origen.is_dir():
        print(f"ERROR: la carpeta de origen no existe: {origen}")
        return 2
    print()

    hallados = descubrir(origen)
    print("-- archivos encontrados por tipo:",
          {k: len(v) for k, v in hallados.items()})
    print()

    resultados: dict[str, tuple[Path, int]] = {}
    for tipo in ("estudiante", "oa", "habilidad"):
        paths = hallados[tipo]
        if not paths:
            print(f"[{tipo}] sin archivos, se omite.")
            continue
        print(f"[{tipo}]")
        if args.sin_dedup:
            pares = [(p, pd.read_excel(p, sheet_name=0, header=0, engine="openpyxl", dtype=str))
                     for p in paths]
            dropped = []
        else:
            pares, dropped = canonicos(paths)
        print(f"  archivos: {len(paths)} | canonicos: {len(pares)} | duplicados descartados: {len(dropped)}")
        for dup, orig in dropped:
            print(f"     dup: {dup.name}  [{dup.parent.name}] == [{orig.parent.name}]")

        d = construir(tipo, pares, args.anio, args.mes)
        destino = escribir(d, tipo, salida)
        resultados[tipo] = (destino, len(d))
        print(f"  -> {destino.name}: {len(d)} filas, {destino.stat().st_size:,} bytes")
        print()

    # ---------------- resumen ----------------
    print("=" * 92)
    print("RESUMEN")
    print("=" * 92)
    for tipo, (destino, n) in resultados.items():
        print(f"  {ARCHIVOS_SALIDA[tipo]:38s} {n:6d} filas  {destino.stat().st_size:>10,} bytes")
    print()
    for tipo, (destino, _) in resultados.items():
        d = pd.read_excel(destino, sheet_name=HOJA_SALIDA, engine="openpyxl")
        print(f"-- desglose {tipo} por (Año, Mes, Asignatura, Nivel)")
        if len(d):
            g = d.groupby(["Año", "Mes", "Asignatura", "Nivel"], dropna=False).size()
            print(g.to_string())
        else:
            print("   (vacio)")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
