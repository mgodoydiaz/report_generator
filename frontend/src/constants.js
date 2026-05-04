/**
 * Archivo central de constantes para el frontend.
 * Permite gestionar URLs, opciones de selectores y estilos globales en un solo lugar.
 */

// URL base de la API — configurable por ambiente via VITE_API_BASE_URL
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

// Opciones de formatos de entrada y salida permitidos
export const FORMAT_OPTIONS = ["", "EXCEL", "PDF", "DOC", "IMG", "DB"];

// Lista de pasos disponibles
export const STEP_OPTIONS = [
  "InitRun",
  "LoadConfigFromSpec",
  "RequestUserFiles",
  "RunExcelETL",
  "RunDIAPDFExtraction",
  "EnrichWithUserInput",
  "EnrichWithContext",
  "EnrichWithLookup",
  "ModifyColumnValues",
  "ApplyDerivedFields",
  "ValidateDataframe",
  "LoadMetricToDF",
  "SaveToMetric",
  "RenderHtmlReport",
  "RenderPDFReport",
];

// Traducciones a lenguaje humano para los pasos técnicos
export const STEP_TRANSLATIONS = {
  "InitRun": "Inicializar Proceso",
  "LoadConfigFromSpec": "Cargar Especificación",
  "RequestUserFiles": "Solicitar Archivos",
  "RunExcelETL": "Procesar Excel",
  "RunDIAPDFExtraction": "Procesar PDFs DIA",
  "EnrichWithUserInput": "Enriquecer por Usuario",
  "EnrichWithContext": "Enriquecer por Contexto",
  "EnrichWithLookup": "Enriquecer con Lookup",
  "ModifyColumnValues": "Modificar Valores",
  "ApplyDerivedFields": "Aplicar Campos Derivados",
  "ValidateDataframe": "Validar DataFrame",
  "LoadMetricToDF": "Cargar Métrica como DataFrame",
  "SaveToMetric": "Cargar Métricas",
  "RenderHtmlReport": "Generar Informe HTML→PDF",
  "RenderPDFReport": "Generar Informe Indicador",
};

// Mapeo de colores y estilos para los formatos de archivo
export const FORMAT_COLORS = {
  'EXCEL': 'bg-emerald-50 text-emerald-600 border-emerald-100',
  'PDF': 'bg-rose-50 text-rose-600 border-rose-100',
  'DOC': 'bg-sky-50 text-sky-600 border-sky-100',
  'IMG': 'bg-amber-50 text-amber-600 border-amber-100',
  'DB': 'bg-violet-50 text-violet-600 border-violet-100'
};

// Tipos de Especificaciones
export const SPEC_TYPES = ["Reporte", "Dashboard", "ETL Archivo", "Gráficos", "Tablas"];

// Opciones de parámetros para ETL
export const ETL_PARAMETER_OPTIONS = [
  { id: 'header_row', label: 'Fila Encabezado', type: 'text', limit: 1 },
  { id: 'output_name', label: 'Nombre Salida', type: 'text', limit: 1 },
  { id: 'select_columns', label: 'Seleccionar Columnas', type: 'list_text', limit: 0 },
  { id: 'rename_columns', label: 'Renombrar Columnas', type: 'list_pair', limit: 0, fields: ['Original', 'Final'] },
  { id: 'enrich_data', label: 'Enriquecer Data', type: 'list_pair', limit: 0, fields: ['Columna', 'Valor'] }
];

/**
 * Helper para obtener el estilo de un formato de forma segura.
 * @param {string} format - El formato (ej: 'EXCEL', 'PDF')
 * @returns {string} Clases de Tailwind para el estilo
 */
export const getFormatStyle = (format) => {
  if (!format) return 'bg-slate-50 text-slate-500 border-slate-100';
  return FORMAT_COLORS[format.toUpperCase()] || 'bg-slate-50 text-slate-500 border-slate-100';
};

/**
 * Elimina comentarios de línea (//) de un string JSONC,
 * respetando strings entre comillas.
 * @param {string} str - String JSONC con comentarios
 * @returns {string} JSON limpio listo para JSON.parse()
 */
export const stripJsonComments = (str) => {
  return str.replace(/("(?:[^"\\]|\\.)*")|\/\/.*/g, (match, group) => {
    return group ? group : '';
  });
};

/**
 * Plantillas JSONC con comentarios explicativos para cada paso del pipeline.
 * Se muestran al usuario al seleccionar un paso en el editor de parámetros.
 */
export const STEP_DEFAULT_PARAMS = {

  "InitRun": `{
  "evaluation": "nombre_evaluacion", // Nombre de la evaluación
  "base_dir": "./data" // Directorio base de trabajo
}`,

  "LoadConfigFromSpec": `{
  "spec_id": 1, // ID del spec/template en la base de datos (obligatorio)
  "config_key": "estudiantes" // (opcional) aísla la config por artifact (estudiantes/preguntas/...)
}`,

  "RequestUserFiles": `{
  "file_specs": [
    {
      "id": "nombre_artifact", // Identificador único del grupo de archivos
      "label": "Nombre en el Modal", // Título visible para el usuario
      "description": "Descripción del archivo requerido", // Texto descriptivo
      "multiple": true, // Permitir múltiples archivos
      "optional": false // Archivo obligatorio u opcional
    }
  ]
}`,

  "RunExcelETL": `{
  "input_key": "nombre_input", // Clave del artifact de entrada
  "output_key": "nombre_output" // Clave del artifact de salida
  // Parámetros opcionales que normalmente vienen del spec (LoadConfigFromSpec):
  // "header_row": 12, // int o {nombre_archivo: int, "default": int}
  // "select_columns": ["col1", "col2"],
  // "rename_columns": {"col_original": "col_final"},
  // "metadata_cells": [ // celdas pre-header a inyectar como columna (caso DIA)
  //   {"column_name": "Establecimiento", "cell": "B5"},
  //   {"column_name": "Curso",           "cell": "B6"}
  // ]
}`,

  "EnrichWithUserInput": `{
  "input_key": "nombre_input" // Clave del artifact de entrada (opcional, se auto-detecta)
  // Los campos a solicitar se leen desde enrich_data del spec (user_input: true)
}`,

  "EnrichWithContext": `{
  "input_key": "nombre_input", // Clave del artifact de entrada
  "output_key": "nombre_output", // Clave del artifact de salida
  "context_mapping": {
    "columna_nueva": "clave_del_contexto" // Mapa columna → parámetro del contexto
  }
}`,

  "EnrichWithLookup": `{
  "input_key": "df_principal", // Clave del artifact principal en ctx.artifacts
  "lookup_key": "df_lookup", // Clave del artifact de lookup en ctx.artifacts
  "on": "ColumnaLlave", // Columna llave compartida (usar si tiene el mismo nombre en ambos lados)
  // "left_on": "ID_Principal", // Columna llave en el artifact principal (usar con right_on)
  // "right_on": "ID_Lookup", // Columna llave en el artifact de lookup (usar con left_on)
  "columns": ["Col1", "Col2"], // Columnas del lookup a incorporar al artifact principal
  "output_key": "df_enriquecido", // Clave del artifact de salida
  "how": "inner" // Tipo de join: inner, left, right, outer
}`,

  "ModifyColumnValues": `{
  "input_key": "nombre_input", // Clave del artifact de entrada
  "output_key": "nombre_output", // Clave del artifact de salida
  "transformations": [
    {
      "columna": "NombreColumna", // Columna a modificar
      "operacion": "replace", // replace | math
      "valor_completo": false, // false (default): busca patron en cualquier parte (regex) | true: coincidencia exacta
      "default": null, // Solo con valor_completo=true. null mantiene el valor original si no hay coincidencia
      "valores": [
        { "patron": "texto_a_buscar", "reemplazo": "texto_nuevo" }
      ]
    }
    // {
    //   "columna": "NombreColumna",
    //   "operacion": "math",
    //   "valores": [
    //     { "condicion": "x > 1", "expresion": "x / 100" }, // condicion booleana con "x"
    //     { "condicion": "*",     "expresion": "x" }        // "*" aplica a todos los valores
    //   ]
    // }
  ]
}`,

  "ApplyDerivedFields": `{
  "input_key": "nombre_input", // Clave del artifact (DataFrame)
  "output_key": "nombre_output", // Clave del artifact resultante
  "derived_fields": [
    // Kinds disponibles: agg | slope | delta | row_mean_dynamic | row_threshold |
    //                    normalize_name | lookup_range | lookup_dict
    // Ejemplos:
    // {"kind": "agg",   "name": "Logro_Promedio_Estudiante",
    //  "value_field": "Logro", "entity_field": "Rut", "agg": "mean"},
    // {"kind": "slope", "name": "Avance",
    //  "value_field": "Logro", "entity_field": "Rut",
    //  "time_field": "Numero_Prueba", "min_points": 2},
    // {"kind": "delta", "name": "Mejora_vs_Inicio",
    //  "value_field": "Logro", "entity_field": "Rut", "time_field": "Numero_Prueba"},
    // {"kind": "row_mean_dynamic", "name": "Logro",
    //  "exclude_columns": ["Numero Lista", "Nombre", "Curso"], "scale": 0.01},
    // {"kind": "row_threshold", "name": "Nivel Logro", "value_field": "Logro",
    //  "thresholds": [
    //    {"max": 0.4,  "label": "Inicial"},
    //    {"max": 0.6,  "label": "Intermedio"},
    //    {"max": null, "label": "Avanzado"}
    //  ]},
    // {"kind": "normalize_name", "name": "Nombre_Norm", "value_field": "Nombre"},
    // {"kind": "lookup_range", "name": "Nivel Establecimiento",
    //  "value_field": "Logro",
    //  "ranges": [
    //    {"min": null, "max": 0.4,  "label": "Insuficiente"},
    //    {"min": 0.4,  "max": 0.7,  "label": "Adecuado"},
    //    {"min": 0.7,  "max": null, "label": "Avanzado"}
    //  ]},
    // {"kind": "lookup_dict", "name": "Nivel", "value_field": "Curso",
    //  "extract": {"split": " ", "index": 0},
    //  "mapping": {"1": "Primeros", "I": "Primeros Medios"}}
  ]
}`,

  "LoadMetricToDF": `{
  "metric_id": 1, // ID de la métrica a cargar
  "output_key": "nombre_artifact", // Clave del artifact de salida (DataFrame)
  "filters": { // (opcional) Filtros exactos por nombre de dimensión
    // "Año": "2024",
    // "Curso": "4B"
  }
}`,

  "SaveToMetric": `{
  "metric_id": 1, // ID de la métrica destino
  "input_key": "nombre_artifact", // Clave del artifact (DataFrame)
  "clear_existing": false // Borrar datos previos antes de insertar
}`,

  "ValidateDataframe": `{
  "input_key": "nombre_input", // Clave del artifact (DataFrame) a validar
  "mode": "strict", // strict (lanza ValueError) | warn (loguea y pasa)
  "schema": {
    "required_columns": ["Logro", "Curso", "Hito"],
    "min_rows": 1,
    "columns": {
      "Logro": {"type": "float", "min": 0, "max": 1, "nullable": false},
      "Curso": {"type": "str", "regex": "^[1-9I]+ ?[A-Z]?$"},
      "Hito":  {"type": "str", "allowed": ["DIAGNOSTICO","INTERMEDIO","FINAL"]}
    }
  }
}`,

  "RunDIAPDFExtraction": `{
  "input_key": "preguntas", // Clave del artifact con los PDFs DIA (un PDF por curso)
  "output_key": "preguntas_raw" // Clave del DataFrame resultante
  // El step detecta automáticamente la sección 'Resultados por pregunta',
  // extrae las tablas con camelot+fitz, identifica la respuesta correcta
  // por análisis de píxeles (texto en negrita) y produce un df con columnas
  // [N Pregunta, Eje Temático, Habilidad, Indicador, % respuestas, Logro,
  //  Establecimiento, Curso].
}`,

  "RenderHtmlReport": `{
  "report_schema": {}, // Estructura del informe (variables_documento + secciones_*)
  "output_filename": "informe.pdf",
  "template_name": "report_latex_paridad.html"
}`,

  "RenderPDFReport": `{
  "indicator_id": 1 // ID del indicador con pdf_layout configurado
}`,

};
