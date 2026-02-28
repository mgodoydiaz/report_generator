/**
 * Archivo central de constantes para el frontend.
 * Permite gestionar URLs, opciones de selectores y estilos globales en un solo lugar.
 */

// URL base de la API
export const API_BASE_URL = "http://localhost:8000/api";

// Opciones de formatos de entrada y salida permitidos
export const FORMAT_OPTIONS = ["", "EXCEL", "PDF", "DOC", "IMG", "DB"];

// Lista de pasos disponibles
export const STEP_OPTIONS = [
  "InitRun",
  // "LoadConfig",  // DEPRECADO: usar LoadConfigFromSpec
  "LoadConfigFromSpec",
  "DiscoverInputs",
  "RequestUserFiles",
  "RunExcelETL",
  "EnrichWithUserInput",
  "EnrichWithContext",
  "SaveToMetric",
  "ExportConsolidatedExcel",
  "GenerateGraphics",
  "GenerateTables",
  "RenderReport",
  "GenerateDocxReport",
  "DeleteTempFiles",

];

// Traducciones a lenguaje humano para los pasos técnicos
export const STEP_TRANSLATIONS = {
  "InitRun": "Inicializar Proceso",
  // "LoadConfig": "Cargar Configuración",  // DEPRECADO
  "LoadConfigFromSpec": "Cargar Especificación",
  "DiscoverInputs": "Identificar Archivos",
  "RequestUserFiles": "Solicitar Archivos",
  "RunExcelETL": "Procesar Datos",
  "EnrichWithUserInput": "Enriquecer por Usuario",
  "EnrichWithContext": "Enriquecer por Contexto",
  "SaveToMetric": "Cargar Métricas",
  "ExportConsolidatedExcel": "Exportar Datos",
  "GenerateGraphics": "Crear Gráficos",
  "GenerateTables": "Preparar Tablas",
  "RenderReport": "Generar Informe PDF",
  "GenerateDocxReport": "Generar Documento DOCX",
  "DeleteTempFiles": "Limpiar Archivos"
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
export const SPEC_TYPES = ["Reporte", "Dashboard", "ETL Archivo"];

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
  "base_dir": "./backend/tests" // Directorio base de trabajo
}`,
  // "LoadConfig": DEPRECADO - usar LoadConfigFromSpec
  "LoadConfigFromSpec": `{
  "spec_id": 1 // ID del spec/template en la base de datos (obligatorio)
}`,
  "DiscoverInputs": `{
  "rules": {
    "tipo_archivo": {
      "extension": ".xlsx", // Extensión del archivo
      "contains": "texto_en_nombre" // Texto que debe contener el nombre
    }
  }
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
  "SaveToMetric": `{
  "metric_id": 1, // ID de la métrica destino
  "input_key": "nombre_artifact", // Clave del artifact (DataFrame)
  "clear_existing": false // Borrar datos previos antes de insertar
}`,
  "ExportConsolidatedExcel": `{
  "input_key": "nombre_input", // Clave del artifact de entrada
  "output_filename": "archivo_salida.xlsx" // Nombre del archivo Excel de salida
}`,
  "GenerateGraphics": `{
  // Lee charts_schema desde ctx.params (cargado por un step previo)
  // No requiere parámetros directos
}`,
  "GenerateTables": `{
  // Lee tables_schema desde ctx.params (cargado por un step previo)
  // No requiere parámetros directos
}`,
  "RenderReport": `{
  "report_schema": {} // Estructura del informe PDF
}`,
  "GenerateDocxReport": `{
  "template_name": "plantilla.docx", // Nombre de la plantilla Word
  "output_filename": "informe.docx", // Nombre del archivo de salida
  "convert_to_pdf": true // Convertir a PDF después de generar
}`,
  "DeleteTempFiles": `{
  // Este paso no requiere parámetros
}`
};
