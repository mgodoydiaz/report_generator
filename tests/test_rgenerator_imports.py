"""Smoke tests that ensure the rgenerator package surface can be imported."""


def test_rgenerator_main_package():
    import rgenerator

    assert hasattr(rgenerator, "tooling")
    assert hasattr(rgenerator, "etl")
    assert hasattr(rgenerator, "reports")


def test_tooling_reexports_from_package():
    from rgenerator import tooling

    expected_attrs = [
        "grafico_barras_promedio_por",
        "boxplot_valor_por_curso",
        "alumnos_por_nivel_cualitativo",
        "alumnos_por_nivel_curso_y_mes",
        "valor_promedio_agrupado_por",
        "resumen_estadistico_basico",
        "tabla_logro_por_alumno",
        "tabla_logro_por_pregunta",
        "formato_informe_generico",
        "indice_alfabetico",
    ]

    missing = [attr for attr in expected_attrs if not hasattr(tooling, attr)]
    assert not missing, f"Atributos faltantes en rgenerator.tooling: {missing}"
