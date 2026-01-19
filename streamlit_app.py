import streamlit as st
import pandas as pd
from streamlit_utils import apply_style, load_excel, get_data_path, to_float

st.set_page_config(page_title="Reportes Academicos", layout="wide")
apply_style()

raw_path = get_data_path("simce_2025_estudiantes.xlsx")
raw_df = load_excel(raw_path)

students = "--"
avg_simce = "--"
avg_logro = "--"

if raw_df is not None:
    if "RUT" in raw_df.columns:
        students = f"{raw_df['RUT'].nunique():,}".replace(",", ".")
    else:
        students = f"{len(raw_df):,}".replace(",", ".")

    if "SIMCE" in raw_df.columns:
        avg_simce = f"{raw_df['SIMCE'].mean():.0f} pts"

    if "Logro" in raw_df.columns:
        avg_logro_value = raw_df["Logro"].apply(to_float).dropna().mean()
        if pd.notna(avg_logro_value):
            avg_logro = f"{avg_logro_value:.1f}%"

st.markdown(
    """
    <section class="hero">
        <div>
            <p class="eyebrow">Panel principal</p>
            <h1>Generador de Reportes Academicos</h1>
            <p class="hero-sub">Explora evaluaciones, monitorea resultados y comparte graficos en tiempo real.</p>
        </div>
        <div class="hero-panel">
            <div class="kpi">
                <span class="kpi-label">Estudiantes evaluados</span>
                <span class="kpi-value">{students}</span>
            </div>
            <div class="kpi">
                <span class="kpi-label">Promedio SIMCE</span>
                <span class="kpi-value">{avg_simce}</span>
            </div>
            <div class="kpi">
                <span class="kpi-label">Logro promedio</span>
                <span class="kpi-value">{avg_logro}</span>
            </div>
        </div>
    </section>
    """.format(students=students, avg_simce=avg_simce, avg_logro=avg_logro),
    unsafe_allow_html=True,
)

st.markdown("<h2 class='section-title'>Accesos rapidos</h2>", unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
        <div class="feature-card">
            <h3>Evaluaciones</h3>
            <p>Administra pruebas, fechas y configuraciones.</p>
            <span class="feature-foot">Ir a Evaluaciones desde el menu lateral.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.markdown(
        """
        <div class="feature-card">
            <h3>Resultados</h3>
            <p>Graficos en vivo con indicadores por curso.</p>
            <span class="feature-foot">Panel BI con tendencias y promedios.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col3:
    st.markdown(
        """
        <div class="feature-card">
            <h3>Exportables</h3>
            <p>Descarga reportes y tablas consolidadas.</p>
            <span class="feature-foot">Datos listos para presentacion.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<h2 class='section-title'>Resumen operativo</h2>", unsafe_allow_html=True)
summary_cols = st.columns(2)

with summary_cols[0]:
    st.markdown(
        """
        <div class="info-card">
            <h4>Carga de datos</h4>
            <p>Se toman archivos desde <strong>data/output</strong>. Puedes reemplazarlos para refrescar el dashboard.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with summary_cols[1]:
    st.markdown(
        """
        <div class="info-card">
            <h4>Estilo dashboard</h4>
            <p>Paleta con alto contraste, tarjetas y secciones listas para BI.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
