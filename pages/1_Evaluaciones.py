import streamlit as st
import pandas as pd
from streamlit_utils import apply_style

st.set_page_config(page_title="Evaluaciones", layout="wide")
apply_style()

st.markdown("<h1 class='page-title'>Evaluaciones configuradas</h1>", unsafe_allow_html=True)
st.markdown("<p class='page-sub'>Administra los tipos de pruebas disponibles.</p>", unsafe_allow_html=True)

records = [
    {
        "Evaluacion": "SIMCE Matematicas",
        "Descripcion": "Ensayo nacional para medicion de habilidades logico-matematicas.",
        "Estado": "Activa",
        "Actualizacion": "08 Ene 2026",
    },
    {
        "Evaluacion": "SIMCE Lenguaje",
        "Descripcion": "Comprension lectora y vocabulario contextual.",
        "Estado": "Activa",
        "Actualizacion": "08 Ene 2026",
    },
    {
        "Evaluacion": "DIA Matematicas",
        "Descripcion": "Diagnostico integral de aprendizajes: numeros y geometria.",
        "Estado": "Activa",
        "Actualizacion": "20 Dic 2025",
    },
    {
        "Evaluacion": "DIA Lenguaje",
        "Descripcion": "Diagnostico integral de aprendizajes: lectura.",
        "Estado": "Activa",
        "Actualizacion": "20 Dic 2025",
    },
    {
        "Evaluacion": "Calculo Veloz",
        "Descripcion": "Medicion de velocidad y precision en operaciones basicas.",
        "Estado": "Interna",
        "Actualizacion": "14 Ene 2026",
    },
    {
        "Evaluacion": "Fluidez Lectora",
        "Descripcion": "Evaluacion de palabras por minuto y calidad lectora.",
        "Estado": "Interna",
        "Actualizacion": "10 Ene 2026",
    },
]

st.dataframe(pd.DataFrame(records), use_container_width=True, hide_index=True)

st.markdown("<h2 class='section-title'>Acciones rapidas</h2>", unsafe_allow_html=True)
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    selection = st.selectbox("Selecciona evaluacion", [r["Evaluacion"] for r in records])

with col2:
    st.button("Duplicar")

with col3:
    st.button("Eliminar")

st.markdown(
    """
    <div class="info-card">
        <h4>Tip de gestion</h4>
        <p>Configura pesos y parametros en la tabla de datos base para actualizar calculos automaticamente.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
