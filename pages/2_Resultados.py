import pandas as pd
import streamlit as st
from streamlit_utils import apply_style, get_data_path, load_excel, to_float

st.set_page_config(page_title="Resultados", layout="wide")
apply_style()

raw_path = get_data_path("simce_2025_estudiantes.xlsx")
summary_simce_path = get_data_path("resumen_simce_por_curso.xlsx")
summary_logro_path = get_data_path("resumen_logro_por_curso.xlsx")
results_path = get_data_path("resultados_estudiantes.xlsx")

raw_df = load_excel(raw_path)
summary_simce = load_excel(summary_simce_path)
summary_logro = load_excel(summary_logro_path)

st.markdown(
    """
    <section class="hero hero-slim">
        <div>
            <p class="eyebrow">Reporte general</p>
            <h1>Resultados trabajados 2025</h1>
            <p class="hero-sub">Promedios, tendencias y graficos en vivo desde los datos procesados.</p>
        </div>
    </section>
    """,
    unsafe_allow_html=True,
)

kpi_cols = st.columns(3)

students = "--"
avg_simce = "--"
best_course = "--"

if raw_df is not None:
    if "RUT" in raw_df.columns:
        students = f"{raw_df['RUT'].nunique():,}".replace(",", ".")
    else:
        students = f"{len(raw_df):,}".replace(",", ".")

    if "SIMCE" in raw_df.columns:
        avg_simce = f"{raw_df['SIMCE'].mean():.0f} pts"

    if "Curso" in raw_df.columns and "SIMCE" in raw_df.columns:
        best_course = raw_df.groupby("Curso")["SIMCE"].mean().idxmax()

with kpi_cols[0]:
    st.metric("Estudiantes", students)
with kpi_cols[1]:
    st.metric("Promedio SIMCE", avg_simce)
with kpi_cols[2]:
    st.metric("Mejor curso", best_course)

st.markdown("<h2 class='section-title'>Promedios por curso</h2>", unsafe_allow_html=True)

if summary_simce is not None:
    table = summary_simce.copy()
    if summary_logro is not None and "Curso" in summary_logro.columns:
        logro = summary_logro[["Curso", "Promedio"]].copy()
        logro["Promedio"] = logro["Promedio"].apply(to_float)
        logro = logro.rename(columns={"Promedio": "Logro promedio"})
        table = table.merge(logro, on="Curso", how="left")

    table = table.rename(columns={
        "Promedio": "Promedio SIMCE",
        "Minimo": "SIMCE minimo",
        "Maximo": "SIMCE maximo",
    })

    st.dataframe(table, use_container_width=True, hide_index=True)
else:
    st.warning("No se encontro el resumen por curso. Verifica data/output.")

st.markdown("<h2 class='section-title'>Graficos en vivo</h2>", unsafe_allow_html=True)

chart_cols = st.columns(2)

with chart_cols[0]:
    if summary_simce is not None and "Curso" in summary_simce.columns and "Promedio" in summary_simce.columns:
        simce_chart = summary_simce.set_index("Curso")["Promedio"]
        st.bar_chart(simce_chart, use_container_width=True)
    else:
        st.info("No hay datos para el grafico de SIMCE por curso.")

with chart_cols[1]:
    if summary_logro is not None and "Curso" in summary_logro.columns and "Promedio" in summary_logro.columns:
        logro_chart = summary_logro.copy()
        logro_chart["Promedio"] = logro_chart["Promedio"].apply(to_float)
        logro_chart = logro_chart.set_index("Curso")["Promedio"]
        st.bar_chart(logro_chart, use_container_width=True)
    else:
        st.info("No hay datos para el grafico de logro por curso.")

if raw_df is not None and "Mes" in raw_df.columns and "SIMCE" in raw_df.columns:
    st.markdown("<h3 class='section-subtitle'>Evolucion SIMCE por mes</h3>", unsafe_allow_html=True)
    month_order = [
        "Marzo",
        "Abril",
        "Mayo",
        "Junio",
        "Julio",
        "Agosto",
        "Septiembre",
        "Octubre",
        "Noviembre",
        "Diciembre",
    ]
    month_map = {name: index for index, name in enumerate(month_order)}
    simce_month = raw_df.copy()
    simce_month["MesOrden"] = simce_month["Mes"].map(month_map)
    simce_month = simce_month.sort_values("MesOrden")
    simce_series = simce_month.groupby("Mes")["SIMCE"].mean()
    st.line_chart(simce_series, use_container_width=True)

st.markdown("<h2 class='section-title'>Graficos listos para presentacion</h2>", unsafe_allow_html=True)

image_files = [
    "rendimiento_promedio_por_curso.png",
    "distribucion_puntaje_simce_por_curso.png",
    "evolucion_simce_promedio_por_curso_y_mes.png",
    "evolucion_logro_promedio_por_curso_y_mes.png",
    "logro_promedio_por_eje.png",
    "logro_promedio_por_habilidad.png",
]

image_cols = st.columns(2)
col_index = 0

for image_name in image_files:
    image_path = get_data_path(image_name)
    if not image_path.exists():
        continue
    with image_cols[col_index % 2]:
        st.image(str(image_path), use_container_width=True, caption=image_name.replace("_", " ").replace(".png", ""))
    col_index += 1

st.markdown("<h2 class='section-title'>Descargas</h2>", unsafe_allow_html=True)

if results_path.exists():
    with open(results_path, "rb") as handle:
        st.download_button("Descargar resultados", handle, file_name=results_path.name)
else:
    st.info("resultados_estudiantes.xlsx no se encuentra en data/output.")

if raw_path.exists():
    with open(raw_path, "rb") as handle:
        st.download_button("Descargar datos base", handle, file_name=raw_path.name)
