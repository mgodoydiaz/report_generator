"""Motor PDF v2 — Informe SIMCE Panguipulli.

Variante del informe SIMCE adaptada al esquema de datos del establecimiento
Panguipulli (metrics 24 y 26, ex-EMN Aptus). A diferencia de SIMCE Pullinque:

- No hay puntaje SIMCE estimado (solo % de logro).
- No hay datos por pregunta individual ni por Eje Temático; las habilidades
  vienen pre-agregadas por curso × asignatura × habilidad (metric 26).
- El "Nivel de Logro" se deriva en runtime desde PorcLogro con umbrales
  fijos (D1): <0.40 = Insuficiente, 0.40-0.60 = Elemental, ≥0.60 = Adecuado.

Comparte el orquestador `runtime.py` y las bibliotecas `charts.py`/`tables.py`
con SIMCE Pullinque y DIA.
"""
