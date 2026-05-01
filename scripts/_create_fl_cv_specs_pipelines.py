"""Crea specs y pipelines locales para FL 2026 y CV 2026."""
import psycopg2
import json
import sys

LOCAL = 'postgresql://mgodoy:holapocompadre977@localhost:5432/rgenerator_dev'

# ---------------------------- SPEC FL 2026 ----------------------------
spec_fl_metadata = {
    "etlParams": [
        {"id": "header_row", "type": "text", "value": "0"},
        {"id": "rename_columns", "type": "list_pair", "value": [
            {"key": "Rut", "val": "RUT"},
            {"key": "Prueba", "val": "Evaluación"}
        ]},
        {"id": "enrich_data", "type": "list_pair", "value": [
            {"key": "Año", "val": "", "user_input": True}
        ]}
    ]
}

# ---------------------------- SPEC CV 2026 ----------------------------
spec_cv_metadata = {
    "etlParams": [
        {"id": "header_row", "type": "text", "value": "0"},
        {"id": "rename_columns", "type": "list_pair", "value": [
            {"key": "Rut", "val": "RUT"},
            {"key": "N Evaluación", "val": "N Prueba"}
        ]},
        {"id": "enrich_data", "type": "list_pair", "value": [
            {"key": "Año", "val": "", "user_input": True},
            {"key": "Establecimiento", "val": "PHP Panguipulli"}
        ]}
    ]
}


def build_pipeline_fl(spec_id):
    return {
        "pipeline_metadata": {
            "name": "Cargar Fluidez Lectora 2026",
            "description": "ETL del xlsx con formato Establecimiento/Prueba/Curso/Fecha/Seguimiento/Rut/Nombre/Cantidad/Categoria/Calidad lectora -> metric_data id=10",
            "input": "EXCEL",
            "output": "DB",
        },
        "context": {},
        "pipeline": [
            {"step": "InitRun", "description": "Inicializa el run",
             "params": {"evaluation": "fluidez_lectora_2026"}},
            {"step": "LoadConfigFromSpec", "description": "Carga spec ETL FL",
             "params": {"spec_id": spec_id, "config_key": "resultados"}},
            {"step": "RequestUserFiles", "description": "Solicita el archivo de resultados",
             "params": {"file_specs": [{"key": "resultados",
                                        "label": "Resultados Fluidez Lectora 2026 (xlsx)",
                                        "accept": ".xlsx,.xls"}]}},
            {"step": "EnrichWithUserInput", "description": "Pide Año por archivo",
             "params": {"input_key": "resultados"}},
            {"step": "RunExcelETL", "description": "Lee el xlsx, renombra columnas y aplica enrich por archivo",
             "params": {"input_key": "resultados", "output_key": "df_fl_raw"}},
            {"step": "ModifyColumnValues",
             "description": "Deriva Mes (Fecha->MM) y Nivel (Curso->primeras palabras)",
             "params": {
                "input_key": "df_fl_raw",
                "output_key": "df_fl_processed",
                "transformations": [
                    {"columna": "Mes", "operacion": "math", "usa_fila": True, "valores": [
                        {"condicion": "hasattr(row['Fecha'], 'month')",
                         "expresion": "f\"{row['Fecha'].month:02d}\""},
                        {"condicion": "*", "expresion": "str(row['Fecha'])[5:7]"}
                    ]},
                    {"columna": "Nivel", "operacion": "math", "usa_fila": True, "valores": [
                        {"condicion": "' ' in str(row['Curso'])",
                         "expresion": "' '.join(str(row['Curso']).split(' ')[:-1])"},
                        {"condicion": "*", "expresion": "str(row['Curso'])"}
                    ]}
                ]
             }},
            {"step": "SaveToMetric", "description": "Guarda en metric_data id=10",
             "params": {"metric_id": 10, "input_key": "df_fl_processed", "clear_existing": False}},
        ],
    }


def build_pipeline_cv(spec_id):
    return {
        "pipeline_metadata": {
            "name": "Cargar Cálculo Veloz 2026",
            "description": "ETL del xlsx con formato Curso/Mes/N Evaluación/Fecha/Rut/Nombre/Apellido/Puntaje/Nota -> metric_data id=9. Calcula Nivel y Nota desde Puntaje.",
            "input": "EXCEL",
            "output": "DB",
        },
        "context": {},
        "pipeline": [
            {"step": "InitRun", "description": "Inicializa el run",
             "params": {"evaluation": "calculo_veloz_2026"}},
            {"step": "LoadConfigFromSpec", "description": "Carga spec ETL CV",
             "params": {"spec_id": spec_id, "config_key": "resultados"}},
            {"step": "RequestUserFiles", "description": "Solicita el archivo de resultados",
             "params": {"file_specs": [{"key": "resultados",
                                        "label": "Resultados Cálculo Veloz 2026 (xlsx)",
                                        "accept": ".xlsx,.xls"}]}},
            {"step": "EnrichWithUserInput", "description": "Pide Año por archivo",
             "params": {"input_key": "resultados"}},
            {"step": "RunExcelETL", "description": "Lee el xlsx y renombra columnas",
             "params": {"input_key": "resultados", "output_key": "df_cv_raw"}},
            {"step": "ModifyColumnValues",
             "description": "Concatena Nombre+Apellido y calcula Nivel/Nota desde Puntaje",
             "params": {
                "input_key": "df_cv_raw",
                "output_key": "df_cv_processed",
                "transformations": [
                    {"columna": "Nombre", "operacion": "math", "usa_fila": True, "valores": [
                        {"condicion": "'Apellido' in row.index and row.get('Apellido')",
                         "expresion": "f\"{row['Nombre']} {row['Apellido']}\""},
                        {"condicion": "*", "expresion": "row['Nombre']"}
                    ]},
                    {"columna": "Nivel", "operacion": "math", "usa_fila": True, "valores": [
                        {"condicion": "row['Puntaje'] <= 39", "expresion": "'INICIAL'"},
                        {"condicion": "row['Puntaje'] <= 59", "expresion": "'BÁSICO'"},
                        {"condicion": "row['Puntaje'] <= 72", "expresion": "'INTERMEDIO'"},
                        {"condicion": "row['Puntaje'] <= 85", "expresion": "'AVANZADO'"},
                        {"condicion": "*", "expresion": "'EXPERTO'"}
                    ]},
                    {"columna": "Nota", "operacion": "math", "usa_fila": True, "valores": [
                        {"condicion": "row['Puntaje'] >= 60",
                         "expresion": "round(0.075 * row['Puntaje'] - 0.5, 2)"},
                        {"condicion": "*",
                         "expresion": "round(0.016667 * row['Puntaje'] + 1, 2)"}
                    ]}
                ]
             }},
            {"step": "SaveToMetric", "description": "Guarda en metric_data id=9",
             "params": {"metric_id": 9, "input_key": "df_cv_processed", "clear_existing": False}},
        ],
    }


def main():
    conn = psycopg2.connect(LOCAL)
    cur = conn.cursor()
    try:
        # Idempotencia: borrar specs/pipelines previos con el mismo nombre
        for spec_name in ['ETL Fluidez Lectora 2026', 'ETL Cálculo Veloz 2026']:
            cur.execute("DELETE FROM specs WHERE name=%s AND org_id=1;", (spec_name,))
        for pipe_name in ['Cargar Fluidez Lectora 2026', 'Cargar Cálculo Veloz 2026']:
            cur.execute("DELETE FROM pipelines WHERE pipeline=%s AND org_id=1;", (pipe_name,))

        cur.execute(
            "INSERT INTO specs (name, type, metadata, charts_list, tables_list, org_id) "
            "VALUES (%s, %s, %s, '[]', '[]', 1) RETURNING id_spec;",
            ('ETL Fluidez Lectora 2026', 'ETL Archivo',
             json.dumps(spec_fl_metadata, ensure_ascii=False))
        )
        spec_fl_id = cur.fetchone()[0]
        print(f'Spec FL 2026: id={spec_fl_id}')

        cur.execute(
            "INSERT INTO specs (name, type, metadata, charts_list, tables_list, org_id) "
            "VALUES (%s, %s, %s, '[]', '[]', 1) RETURNING id_spec;",
            ('ETL Cálculo Veloz 2026', 'ETL Archivo',
             json.dumps(spec_cv_metadata, ensure_ascii=False))
        )
        spec_cv_id = cur.fetchone()[0]
        print(f'Spec CV 2026: id={spec_cv_id}')

        cur.execute(
            "INSERT INTO pipelines (pipeline, description, config_json, hidden, org_id) "
            "VALUES (%s, %s, %s, false, 1) RETURNING pipeline_id;",
            ('Cargar Fluidez Lectora 2026',
             'Sube xlsx según formato adjunto. Pide Año por archivo y deriva Mes/Nivel automáticamente.',
             json.dumps(build_pipeline_fl(spec_fl_id), ensure_ascii=False))
        )
        pipe_fl_id = cur.fetchone()[0]
        print(f'Pipeline FL 2026: id={pipe_fl_id}')

        cur.execute(
            "INSERT INTO pipelines (pipeline, description, config_json, hidden, org_id) "
            "VALUES (%s, %s, %s, false, 1) RETURNING pipeline_id;",
            ('Cargar Cálculo Veloz 2026',
             'Sube xlsx según formato adjunto. Calcula Nivel desde Puntaje (rangos PHP) y Nota desde Puntaje (tramos lineales). Pide Año por archivo.',
             json.dumps(build_pipeline_cv(spec_cv_id), ensure_ascii=False))
        )
        pipe_cv_id = cur.fetchone()[0]
        print(f'Pipeline CV 2026: id={pipe_cv_id}')

        conn.commit()
        print('\nCOMMIT OK')
    except Exception as e:
        conn.rollback()
        print('ROLLBACK:', e)
        sys.exit(1)
    finally:
        cur.close(); conn.close()


if __name__ == '__main__':
    main()
