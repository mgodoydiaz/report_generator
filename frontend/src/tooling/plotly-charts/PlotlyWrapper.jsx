import React from 'react';
import Plot from 'react-plotly.js';

const BASE_FONT = { family: 'Inter, system-ui, sans-serif', size: 12, color: '#64748b' };

/**
 * Wrapper compartido para todos los gráficos Plotly.
 * Aplica defaults de apariencia: sin modebar, sin drag, fondos transparentes,
 * fuente Inter, responsive.
 *
 * Props:
 *   data    - array de trazas Plotly
 *   layout  - layout Plotly (se mergea con los defaults)
 *   height  - altura en px (default 280)
 *   wide    - bool, si true usa height más grande (default false)
 */
export default function PlotlyWrapper({ data = [], layout = {}, height, config = {} }) {
    const isDark = document.documentElement.classList.contains('dark');
    const fontColor = isDark ? '#94a3b8' : '#64748b';
    const gridColor = isDark ? '#1e293b' : '#f1f5f9';

    const mergedLayout = {
        autosize: true,
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        dragmode: false,
        margin: { t: 16, r: 16, b: 40, l: 48, pad: 0 },
        font: { ...BASE_FONT, color: fontColor },
        xaxis: {
            gridcolor: gridColor,
            linecolor: gridColor,
            tickfont: { size: 12, color: fontColor },
            ...(layout.xaxis || {}),
        },
        yaxis: {
            gridcolor: gridColor,
            linecolor: gridColor,
            tickfont: { size: 12, color: fontColor },
            zeroline: false,
            ...(layout.yaxis || {}),
        },
        legend: {
            font: { size: 12, color: fontColor },
            bgcolor: 'transparent',
            ...(layout.legend || {}),
        },
        ...layout,
        // These always override user layout to ensure consistent appearance
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        dragmode: false,
    };

    const mergedConfig = {
        responsive: true,
        displayModeBar: false,
        scrollZoom: false,
        staticPlot: false,
        ...config,
    };

    return (
        <Plot
            data={data}
            layout={mergedLayout}
            config={mergedConfig}
            useResizeHandler
            style={{ width: '100%', height: height || 280 }}
        />
    );
}
