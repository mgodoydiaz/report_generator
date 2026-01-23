# Definición de reglas (puede ir en constantes o config)
INPUT_RULES = {
    "estudiantes": {
        "contains": "Resultados",
        "extension": ".xlsx",
        "exclude_prefix": "~$"
    },
    "preguntas": {
        "contains": "ReportePregunta",
        "extension": ".xlsx",
        "exclude_prefix": "~$"
    }
}