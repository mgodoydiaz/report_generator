"""Motor de informes PDF v2 — paridad LaTeX vía matplotlib + WeasyPrint.

Estructura:
    charts.py       biblioteca de funciones matplotlib (gráficos)
    tables.py       biblioteca de funciones pandas → HTML (tablas)
    helpers.py      utilidades comunes (df_a_html_table, embed_png_b64)
    data.py         carga DataFrames desde la DB
    runtime.py      orquestador: combina esquema + funciones → PDF

    templates/      Jinja2 + CSS, replica visual de formato_informe.tex
    assets/         logos oficiales (PHP, Pullinque, etc.)

    simce/          configuración por tipo de informe
    dia/

El contrato: las funciones de charts.py / tables.py son COPIA TEXTUAL de
docs/desarrollo/referencia_informe/SIMCE/funciones.py — generalizadas y
parametrizables. Si un informe necesita un gráfico que no existe, se añade
a charts.py una vez y queda disponible para todos los demás.
"""
