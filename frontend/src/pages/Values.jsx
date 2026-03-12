import React, { useState, useEffect, useMemo } from 'react';
import { Search, Plus, Upload, Download, Trash2, Filter, Layers, Database, AlertCircle, SquarePen } from 'lucide-react';
import toast from 'react-hot-toast';
import { API_BASE_URL } from '../constants';
import NewValueDrawer from '../components/NewValueDrawer';
import ExportModal from '../components/ExportModal';
import ImportModal from '../components/ImportModal';
import ConfirmModal from '../components/ConfirmModal';

export default function Values() {
    const [metrics, setMetrics] = useState([]);
    const [selectedMetric, setSelectedMetric] = useState(null);
    const [metricData, setMetricData] = useState([]);
    const [selectedIds, setSelectedIds] = useState(new Set());
    const [editingData, setEditingData] = useState(null); // Dato siendo editado
    const [dimensionsMap, setDimensionsMap] = useState({}); // {dimId: {name, values: {valId: label}}} para renderizado rápido
    const [loadingMetrics, setLoadingMetrics] = useState(true);
    const [loadingData, setLoadingData] = useState(false);
    const [searchTerm, setSearchTerm] = useState("");

    // Paginación
    const [currentPage, setCurrentPage] = useState(1);
    const [totalRecords, setTotalRecords] = useState(0);
    const PAGE_SIZE = 50;

    // UI States
    const [isDrawerOpen, setIsDrawerOpen] = useState(false);
    const [isExportModalOpen, setIsExportModalOpen] = useState(false);
    const [isImportModalOpen, setIsImportModalOpen] = useState(false);
    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

    useEffect(() => {
        loadInitialData();
    }, []);

    useEffect(() => {
        if (selectedMetric) {
            setCurrentPage(1);
            setSelectedIds(new Set()); // Limpiar selección al cambiar métrica
        } else {
            setMetricData([]);
            setSelectedIds(new Set());
            setTotalRecords(0);
        }
    }, [selectedMetric]);

    useEffect(() => {
        if (selectedMetric) {
            loadMetricData(selectedMetric.id_metric, currentPage);
            setSelectedIds(new Set());
        }
    }, [selectedMetric, currentPage]);

    const loadInitialData = async () => {
        setLoadingMetrics(true);
        try {
            // Cargar Métricas y Dimensiones (con sus valores)
            // Idealmente el backend nos daría todo junto, pero por ahora hacemos varias llamadas o una optimizada
            // Para Values, necesitamos saber los Nombres de las dimensiones y los Nombres de los valores (si son ID).
            // Estrategia: Cargar Métricas y Dimensiones base. Los valores específicos los resolveremos al cargar la data o bajo demanda.

            const [metricsRes, dimsRes] = await Promise.all([
                fetch(`${API_BASE_URL}/metrics`),
                fetch(`${API_BASE_URL}/dimensions`)
            ]);

            const metricsList = await metricsRes.json();
            const dimsList = await dimsRes.json();

            if (metricsList.error) throw new Error(metricsList.error);

            setMetrics(metricsList);

            // Mapa de dimensiones para acceso rápido
            const dMap = {};
            // También cargamos los valores de las dimensiones? 
            // Si la tabla guarda IDs de valores, necesitamos traducir ID -> Texto.
            // Por simplicidad, asumiremos que metric_data guarda el VALOR REAL (texto/id) directamente en el JSON.
            // Si guarda IDs, necesitaríamos hacer un fetch de todos los dimension_values.
            // Para no sobrecargar, cargaremos las definiciones de dimensiones.

            dimsList.forEach(d => {
                dMap[d.id_dimension] = d;
            });
            setDimensionsMap(dMap);

            if (metricsList.length > 0) {
                setSelectedMetric(metricsList[0]);
            }

        } catch (error) {
            toast.error("Error cargando datos: " + error.message);
        } finally {
            setLoadingMetrics(false);
        }
    };

    const loadMetricData = async (metricId, page = 1) => {
        setLoadingData(true);
        try {
            const res = await fetch(`${API_BASE_URL}/metrics/${metricId}/data?page=${page}&page_size=${PAGE_SIZE}`);
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            setMetricData(data.items);
            setTotalRecords(data.total);
        } catch (error) {
            toast.error("Error cargando valores: " + error.message);
        } finally {
            setLoadingData(false);
        }
    };

    const handleDeleteValue = async (dataId) => {
        if (!confirm("¿Eliminar este registro?")) return;
        try {
            await fetch(`${API_BASE_URL}/metrics/data/${dataId}`, { method: 'DELETE' });
            setMetricData(prev => prev.filter(d => d.id_data !== dataId));
            toast.success("Eliminado");
        } catch (error) {
            toast.error(error.message);
        }
    };

    // Selección
    const toggleSelect = (id) => {
        const newSet = new Set(selectedIds);
        if (newSet.has(id)) newSet.delete(id);
        else newSet.add(id);
        setSelectedIds(newSet);
    };

    const toggleSelectAll = () => {
        if (selectedIds.size === metricData.length) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(metricData.map(d => d.id_data)));
        }
    };

    // Paginación helpers
    const totalPages = Math.ceil(totalRecords / PAGE_SIZE);
    const rangeStart = totalRecords === 0 ? 0 : (currentPage - 1) * PAGE_SIZE + 1;
    const rangeEnd = Math.min(currentPage * PAGE_SIZE, totalRecords);

    const goToPrevPage = () => setCurrentPage(p => Math.max(1, p - 1));
    const goToNextPage = () => setCurrentPage(p => Math.min(totalPages, p + 1));

    const handleAddValue = () => {
        setEditingData(null); // Modo creación
        if (!selectedMetric) {
            toast.error("Selecciona una métrica primero");
            return;
        }
        setIsDrawerOpen(true);
    };

    const handleEditValue = (row) => {
        setEditingData(row);
        setIsDrawerOpen(true);
    };

    const handleBatchDeleteClick = () => {
        if (selectedIds.size === 0) return;
        setIsDeleteModalOpen(true);
    };

    const confirmBatchDelete = async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/metrics/data/batch-delete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ids: Array.from(selectedIds) })
            });
            const data = await res.json();
            if (data.error) throw new Error(data.error);

            toast.success(`Eliminados ${data.deleted_count} registros`);
            loadMetricData(selectedMetric.id_metric, currentPage);
            setSelectedIds(new Set());
            setIsDeleteModalOpen(false);
        } catch (error) {
            toast.error("Error eliminando: " + error.message);
        }
    };

    const handleExportClick = () => {
        if (!selectedMetric) return;
        setIsExportModalOpen(true);
    };

    const handleExportConfirm = async (format, fileName) => {
        try {
            const response = await fetch(`${API_BASE_URL}/metrics/${selectedMetric.id_metric}/export?format=${format}`);
            if (!response.ok) throw new Error("Error en la exportación");

            // Convertir respuesta a Blob y descargar
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            // Usar nombre personalizado, asegurarse de tener la extensión correcta
            const ext = format === 'excel' ? 'xlsx' : format;
            a.download = `${fileName}.${ext}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            toast.success("Exportación completada");
        } catch (error) {
            console.error(error);
            toast.error("Error al exportar: " + error.message);
        }
    };

    const handleImportClick = () => {
        if (!selectedMetric) return;
        setIsImportModalOpen(true);
    };

    const handleImportConfirm = async (files) => {
        try {
            const formData = new FormData();
            files.forEach(file => {
                formData.append('files', file);
            });

            const res = await fetch(`${API_BASE_URL}/metrics/${selectedMetric.id_metric}/import`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();

            if (data.error) throw new Error(data.error || "Error importing data");

            toast.success(`Importados ${data.imported} registros correctamente`);
            setCurrentPage(1);
            loadMetricData(selectedMetric.id_metric, 1); // Recargar tabla desde página 1
        } catch (error) {
            console.error(error);
            toast.error("Error al importar: " + error.message);
        }
    };

    const handleDownloadTemplate = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/metrics/${selectedMetric.id_metric}/template`);
            if (!response.ok) throw new Error("Error generando plantilla");

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Plantilla_${selectedMetric.name.replace(/\s+/g, '_')}.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            toast.error(error.message);
        }
    };

    const filteredMetrics = useMemo(() => {
        return metrics.filter(m => m.name.toLowerCase().includes(searchTerm.toLowerCase()));
    }, [metrics, searchTerm]);

    // Columnas Dinámicas
    const dynamicColumns = useMemo(() => {
        if (!selectedMetric) return [];
        const cols = [];

        // 1. Columnas de Dimensiones
        selectedMetric.dimension_ids.forEach(dimId => {
            const dimDef = dimensionsMap[dimId];
            if (dimDef) {
                cols.push({
                    key: `dim_${dimId}`,
                    label: dimDef.name,
                    isDim: true,
                    dimId: dimId
                });
            }
        });

        // 2. Columna(s) de Valor
        if (selectedMetric.data_type === 'object' && selectedMetric.meta_json?.fields) {
            // Si es objeto, creamos una columna por cada campo definido en la estructura
            selectedMetric.meta_json.fields.forEach(field => {
                cols.push({
                    key: `field_${field.name}`,
                    label: field.name,
                    isObjField: true,
                    fieldKey: field.name,
                    fieldType: field.type
                });
            });
        } else {
            // Si es simple, una sola columna Valor
            cols.push({ key: 'value', label: 'Valor', isValue: true });
        }

        return cols;
    }, [selectedMetric, dimensionsMap]);

    return (
        <div className="h-[calc(100vh-100px)] flex gap-6 animate-in fade-in duration-500">
            {/* Sidebar: Lista de Métricas */}
            <div className="w-1/4 min-w-[280px] flex flex-col gap-4 bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 p-4 shadow-sm h-full">
                <div className="pb-2 border-b border-slate-100 dark:border-slate-800 space-y-3">
                    <h2 className="font-black text-slate-800 dark:text-white text-lg px-2 flex items-center gap-2">
                        <Database size={20} className="text-indigo-600" />
                        Métricas
                    </h2>
                    <div className="relative">
                        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Buscar..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full bg-slate-50 dark:bg-slate-800 border-none rounded-xl py-2 pl-9 pr-3 text-sm focus:ring-2 focus:ring-indigo-500/20 text-slate-600 dark:text-slate-300"
                        />
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto custom-scrollbar space-y-1 pr-1">
                    {loadingMetrics ? (
                        <div className="p-4 text-center text-slate-400 text-sm">Cargando métricas...</div>
                    ) : filteredMetrics.map(metric => (
                        <button
                            key={metric.id_metric}
                            onClick={() => setSelectedMetric(metric)}
                            className={`w-full text-left p-3 rounded-xl transition-all border ${selectedMetric?.id_metric === metric.id_metric
                                ? 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-800 shadow-sm'
                                : 'bg-transparent border-transparent hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-500'
                                }`}
                        >
                            <div className="font-bold text-sm text-slate-700 dark:text-slate-200">{metric.name}</div>
                            <div className="flex items-center gap-2 mt-1">
                                <span className="text-[10px] bg-slate-100 dark:bg-slate-700 px-1.5 py-0.5 rounded text-slate-500 font-medium">
                                    {metric.data_type}
                                </span>
                                <span className="text-[10px] text-slate-400 flex items-center gap-1">
                                    <Layers size={10} /> {metric.dimension_ids?.length || 0} dims
                                </span>
                            </div>
                        </button>
                    ))}
                </div>
            </div>

            {/* Main Content: Tabla de Datos */}
            <div className="flex-1 bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col h-full overflow-hidden">
                {!selectedMetric ? (
                    <div className="flex-1 flex flex-col items-center justify-center text-slate-300">
                        <Database size={48} className="mb-4 opacity-50" />
                        <p>Selecciona una métrica para ver sus datos</p>
                    </div>
                ) : (
                    <>
                        {/* Toolbar */}
                        <div className="p-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/30 space-y-3">
                            {/* Fila 1: Título + acciones */}
                            <div className="flex justify-between items-center">
                                <div>
                                    <h1 className="text-xl font-bold text-slate-800 dark:text-white">
                                        {selectedMetric.name}
                                    </h1>
                                    <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">{selectedMetric.description}</p>
                                </div>
                                <div className="flex gap-2 items-center">
                                    {selectedIds.size > 0 && (
                                        <button
                                            onClick={handleBatchDeleteClick}
                                            className="flex items-center gap-2 px-3 py-2.5 text-red-600 bg-red-50 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400 border border-transparent rounded-xl text-sm font-bold transition-all animate-in zoom-in duration-200 mr-2"
                                        >
                                            <Trash2 size={16} /> Eliminar ({selectedIds.size})
                                        </button>
                                    )}
                                    <button onClick={() => toast("Filtros próximamente", { icon: '🚧' })} className="p-2.5 text-slate-400 hover:text-indigo-600 hover:bg-white dark:hover:bg-slate-700 rounded-xl border border-transparent hover:border-slate-200 transition-all" title="Filtrar">
                                        <Filter size={18} />
                                    </button>
                                    <div className="h-8 w-px bg-slate-200 dark:bg-slate-700 mx-1"></div>
                                    <button onClick={handleImportClick} className="flex items-center gap-2 px-4 py-2.5 text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-sm font-bold transition-all">
                                        <Upload size={16} /> Importar
                                    </button>
                                    <button onClick={handleExportClick} className="flex items-center gap-2 px-4 py-2.5 text-slate-600 dark:text-slate-300 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-xl text-sm font-bold transition-all">
                                        <Download size={16} /> Exportar
                                    </button>
                                    <button
                                        onClick={handleAddValue}
                                        className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-bold shadow-lg shadow-indigo-100 dark:shadow-indigo-900/30 transition-all active:scale-95 ml-2"
                                    >
                                        <Plus size={18} strokeWidth={3} /> Agregar Valor
                                    </button>
                                </div>
                            </div>

                            {/* Fila 2: Paginación */}
                            <div className="flex items-center justify-end gap-2">
                                <span className="text-sm text-slate-400 select-none">
                                    {totalRecords === 0
                                        ? '0 registros'
                                        : `${rangeStart}–${rangeEnd} de ${totalRecords}`
                                    }
                                </span>
                                <button
                                    onClick={goToPrevPage}
                                    disabled={currentPage <= 1 || loadingData}
                                    className="flex items-center justify-center w-7 h-7 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all text-sm font-bold"
                                    title="Página anterior"
                                >
                                    ‹
                                </button>
                                <button
                                    onClick={goToNextPage}
                                    disabled={currentPage >= totalPages || loadingData}
                                    className="flex items-center justify-center w-7 h-7 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed transition-all text-sm font-bold"
                                    title="Página siguiente"
                                >
                                    ›
                                </button>
                            </div>
                        </div>

                        {/* Table Area */}
                        <div className="flex-1 overflow-auto">
                            <table className="w-full text-left border-collapse">
                                <thead className="sticky top-0 bg-slate-50 dark:bg-slate-800 z-10 shadow-sm">
                                    <tr>
                                        <th className="p-4 w-10 border-b border-slate-200 dark:border-slate-700">
                                            <input
                                                type="checkbox"
                                                className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                                                checked={metricData.length > 0 && selectedIds.size === metricData.length}
                                                onChange={toggleSelectAll}
                                            />
                                        </th>
                                        {dynamicColumns.map(col => (
                                            <th key={col.key} className="p-4 font-bold text-slate-500 text-xs uppercase tracking-wider border-b border-slate-200 dark:border-slate-700">
                                                {col.label}
                                            </th>
                                        ))}
                                        <th className="p-4 w-20 border-b border-slate-200 dark:border-slate-700"></th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                    {loadingData ? (
                                        <tr><td colSpan={dynamicColumns.length + 1} className="p-10 text-center text-slate-400">Cargando datos...</td></tr>
                                    ) : metricData.length === 0 ? (
                                        <tr>
                                            <td colSpan={dynamicColumns.length + 1} className="p-12 text-center">
                                                <div className="flex flex-col items-center gap-3 text-slate-300">
                                                    <AlertCircle size={32} />
                                                    <p className="font-medium">No hay datos registrados aún.</p>
                                                    <button onClick={handleAddValue} className="text-indigo-500 hover:underline text-sm">Agregar el primer valor</button>
                                                </div>
                                            </td>
                                        </tr>
                                    ) : (
                                        metricData.map(row => (
                                            <tr key={row.id_data} className={`hover:bg-slate-50/80 dark:hover:bg-slate-800/50 group transition-colors ${selectedIds.has(row.id_data) ? 'bg-indigo-50/50 dark:bg-indigo-900/10' : ''}`}>
                                                <td className="p-4 border-b border-slate-50 dark:border-slate-800/50">
                                                    <input
                                                        type="checkbox"
                                                        className="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                                                        checked={selectedIds.has(row.id_data)}
                                                        onChange={() => toggleSelect(row.id_data)}
                                                    />
                                                </td>
                                                {dynamicColumns.map(col => {
                                                    let cellContent = '-';
                                                    if (col.isDim) {
                                                        // Extraer valor del JSON de dimensiones
                                                        cellContent = row.dimensions_json?.[String(col.dimId)] || '-';
                                                    } else if (col.isObjField) {
                                                        // Extraer campo específico del Objeto valor
                                                        try {
                                                            const valObj = typeof row.value === 'string' ? JSON.parse(row.value) : row.value;
                                                            const rawVal = valObj?.[col.fieldKey] ?? '-';

                                                            // Formato básico según tipo (opcional)
                                                            const displayVal = (col.fieldType === 'bool') ? (rawVal ? 'Sí' : 'No') : rawVal;

                                                            cellContent = <span className="font-bold text-slate-700 dark:text-slate-200">{displayVal}</span>;
                                                        } catch {
                                                            cellContent = <span className="text-red-300" title="Error parseando JSON">Error</span>;
                                                        }
                                                    } else if (col.isValue) {
                                                        // Valor Simple con Formato
                                                        let displayVal = row.value;

                                                        try {
                                                            if (selectedMetric.data_type === 'date' && displayVal) {
                                                                // Ajustar zona horaria para evitar desfase si es solo fecha
                                                                // Al crear new Date('YYYY-MM-DD'), JS usa UTC. Al mostar local, puede restar un día.
                                                                // Mejor técnica simple: split y mostrar o usar biblioteca día.
                                                                // Para prototipo: new Date(displayVal + 'T00:00:00') forzando hora local o string directo si ya es YYYY-MM-DD
                                                                // Mostraremos el string tal cual si es corto, o formateado.
                                                                displayVal = new Date(displayVal).toLocaleDateString();
                                                            } else if (selectedMetric.data_type === 'datetime' && displayVal) {
                                                                displayVal = new Date(displayVal).toLocaleString();
                                                            }
                                                        } catch (e) {
                                                            console.warn("Date parse error", e);
                                                        }

                                                        cellContent = <span className="font-bold text-slate-700 dark:text-slate-200">{displayVal}</span>;
                                                    }

                                                    return (
                                                        <td key={col.key} className="p-4 text-sm text-slate-600 dark:text-slate-400 border-b border-slate-50 dark:border-slate-800/50">
                                                            {cellContent}
                                                        </td>
                                                    );
                                                })}
                                                <td className="p-4 text-right border-b border-slate-50 dark:border-slate-800/50">
                                                    <div className="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                        <button
                                                            onClick={() => handleEditValue(row)}
                                                            className="p-1.5 text-slate-300 hover:text-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-lg transition-all"
                                                            title="Editar"
                                                        >
                                                            <SquarePen size={16} />
                                                        </button>
                                                        <button
                                                            onClick={() => handleDeleteValue(row.id_data)}
                                                            className="p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-all"
                                                            title="Eliminar"
                                                        >
                                                            <Trash2 size={16} />
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </>
                )}
            </div>

            {/* Drawer para Agregar/Editar Valor */}
            <NewValueDrawer
                isOpen={isDrawerOpen}
                onClose={() => {
                    setIsDrawerOpen(false);
                    setEditingData(null);
                }}
                metric={selectedMetric}
                dimensionsMap={dimensionsMap}
                onSave={() => loadMetricData(selectedMetric.id_metric, currentPage)}
                initialData={editingData}
            />

            <ExportModal
                isOpen={isExportModalOpen}
                onClose={() => setIsExportModalOpen(false)}
                onExport={handleExportConfirm}
                defaultFileName={selectedMetric ? (() => {
                    const d = new Date();
                    const yyyy = d.getFullYear(); // Usar año completo
                    const mm = String(d.getMonth() + 1).padStart(2, '0');
                    const dd = String(d.getDate()).padStart(2, '0');
                    return `${selectedMetric.name.replace(/\s+/g, '_')}_${yyyy}_${mm}_${dd}`;
                })() : 'export'}
            />

            <ImportModal
                isOpen={isImportModalOpen}
                onClose={() => setIsImportModalOpen(false)}
                onImport={handleImportConfirm}
                onDownloadTemplate={handleDownloadTemplate}
                metricName={selectedMetric?.name}
            />

            <ConfirmModal
                isOpen={isDeleteModalOpen}
                onClose={() => setIsDeleteModalOpen(false)}
                onConfirm={confirmBatchDelete}
                title="Eliminar datos seleccionados"
                message={`¿Estás seguro de que deseas eliminar ${selectedIds.size} registros? Esta acción no se puede deshacer.`}
                confirmText="Sí, Eliminar"
                isDestructive={true}
            />
        </div>
    );
}
