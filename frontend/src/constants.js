/**
 * Archivo central de constantes para el frontend.
 * Permite gestionar URLs, opciones de selectores y estilos globales en un solo lugar.
 */

// URL base de la API
export const API_BASE_URL = "http://localhost:8000/api";

// Opciones de formatos de entrada y salida permitidos
export const FORMAT_OPTIONS = ["EXCEL", "PDF", "DOC", "IMG"];

// Lista de pasos disponibles
export const STEP_OPTIONS = [
    "InitRun",
    "LoadConfig",
    "DiscoverInputs",
    "RequestUserFiles",
    "RunExcelETL",
    "EnrichWithContext",
    "ExportConsolidatedExcel",
    "GenerateGraphics",
    "GenerateTables",
    "RenderReport",
    "GenerateDocxReport",
    "GenerateDocxReport",
    "DeleteTempFiles",
    "LoadToMetrics"
];

// Traducciones a lenguaje humano para los pasos técnicos
export const STEP_TRANSLATIONS = {
    "InitRun": "Inicializar Proceso",
    "LoadConfig": "Cargar Configuración",
    "DiscoverInputs": "Identificar Archivos",
    "RequestUserFiles": "Cargar Archivos",
    "RunExcelETL": "Procesar Datos",
    "EnrichWithContext": "Enriquecer Información",
    "ExportConsolidatedExcel": "Exportar Datos",
    "GenerateGraphics": "Crear Gráficos",
    "GenerateTables": "Preparar Tablas",
    "RenderReport": "Generar Informe",
    "GenerateDocxReport": "Generar Documento",
    "DeleteTempFiles": "Limpiar Archivos",
    "LoadToMetrics": "Cargar Métricas"
};

// Mapeo de colores y estilos para los formatos de archivo
export const FORMAT_COLORS = {
    'EXCEL': 'bg-emerald-50 text-emerald-600 border-emerald-100',
    'PDF': 'bg-rose-50 text-rose-600 border-rose-100',
    'DOC': 'bg-sky-50 text-sky-600 border-sky-100',
    'IMG': 'bg-amber-50 text-amber-600 border-amber-100'
};

// Tipos de Plantillas
export const TEMPLATE_TYPES = ["Reporte", "Dashboard", "ETL Archivo"];

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
