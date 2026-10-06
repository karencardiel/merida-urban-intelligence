"""
Streamlit Geospatial Dashboard: Mérida Urban Intelligence
Run with: streamlit run dashboard/app.py
"""
import sys
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
import numpy as np
from PIL import Image

st.set_page_config(
    page_title="Mérida Urban Intelligence",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Header
st.title("🏛️ Mérida Urban Intelligence: Geospatial Dashboard")
st.markdown(
    "Plataforma analítica y dimensional para la ciudad de Mérida, Yucatán. "
    "Integración territorial de siniestralidad vial, densidad comercial (DENUE) y demografía (Censo 2020)."
)

# Load data
@st.cache_data
def load_data():
    incidents_path = ROOT_DIR / "data" / "processed" / "fact_traffic_incidents.csv"
    types_path = ROOT_DIR / "data" / "processed" / "dim_incident_type.csv"
    
    df_incidents = pd.read_csv(incidents_path)
    df_types = pd.read_csv(types_path)
    
    df_merged = df_incidents.merge(df_types, on="tipo_id", how="left")
    return df_merged

df = load_data()

# Sidebar Filters
st.sidebar.header("Filtros Territoriales")

tipos_disponibles = ["Todos"] + sorted(df["tipo_accidente"].dropna().unique().tolist())
tipo_sel = st.sidebar.selectbox("Tipología de Siniestro:", tipos_disponibles)

dias_disponibles = ["Toda la semana", "Fin de semana (Vie - Dom)", "Entre semana (Lun - Jue)"]
dia_sel = st.sidebar.selectbox("Temporalidad:", dias_disponibles)

alcohol_only = st.sidebar.checkbox("Sólo con aliento alcohólico")
fatal_only = st.sidebar.checkbox("Sólo incidentes graves / fatales")

# Apply filters
df_filtered = df.copy()

if tipo_sel != "Todos":
    df_filtered = df_filtered[df_filtered["tipo_accidente"] == tipo_sel]

if dia_sel == "Fin de semana (Vie - Dom)":
    df_filtered = df_filtered[df_filtered["dia_semana"].isin(["Viernes", "Sábado", "Domingo"])]
elif dia_sel == "Entre semana (Lun - Jue)":
    df_filtered = df_filtered[df_filtered["dia_semana"].isin(["Lunes", "Martes", "Miércoles", "Jueves"])]

if alcohol_only:
    df_filtered = df_filtered[df_filtered["aliento_alcohol"] == True]

if fatal_only:
    df_filtered = df_filtered[(df_filtered["con_fallecidos"] == True) | (df_filtered["con_heridos"] == True)]

# Metrics Row
col1, col2, col3, col4 = st.columns(4)
col1.metric("Siniestros Filtrados", f"{len(df_filtered):,}", f"{len(df):,} totales")
moto_count = (df_filtered["tipo_accidente"] == "Colisión con motocicleta").sum()
col2.metric("Choques en Moto", f"{moto_count:,}", f"{(moto_count/max(len(df_filtered),1)*100):.1f}%")
peaton_count = (df_filtered["tipo_accidente"] == "Colisión con peatón").sum()
col3.metric("Atropellamientos", f"{peaton_count:,}", f"{(peaton_count/max(len(df_filtered),1)*100):.1f}%")
alc_count = (df_filtered["aliento_alcohol"] == True).sum()
col4.metric("Con Alcohol", f"{alc_count:,}", f"{(alc_count/max(len(df_filtered),1)*100):.1f}%")

# Tabs
tab1, tab2, tab3 = st.tabs(["🗺️ Mapa Interactivo", "📊 Mapas Temáticos & LISA", "📈 Estadísticas & Correlación"])

with tab1:
    st.subheader("Mapa Espacial de Incidentes en Mérida")
    # Streamlit native st.map
    st.map(
        df_filtered[["latitud", "longitud"]].rename(columns={"latitud": "latitude", "longitud": "longitude"}),
        zoom=12
    )

with tab2:
    st.subheader("Visualizaciones Cartográficas de Alta Resolución")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Densidad Espacial por Manzana**")
        img1 = Image.open(ROOT_DIR / "outputs" / "maps" / "merida_incident_density_blocks.png")
        st.image(img1, use_column_width=True)
    with c2:
        st.markdown("**Clústeres LISA (Local Moran's I)**")
        img2 = Image.open(ROOT_DIR / "outputs" / "maps" / "lisa_clusters_accidents.png")
        st.image(img2, use_column_width=True)

with tab3:
    st.subheader("Autocorrelación Espacial y Matrices de Correlación")
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**Diagrama de Dispersión de Moran (I = 0.582)**")
        img3 = Image.open(ROOT_DIR / "outputs" / "figures" / "moran_scatterplot_accidents.png")
        st.image(img3, use_column_width=True)
    with c4:
        st.markdown("**Matriz de Correlación de Spearman**")
        img4 = Image.open(ROOT_DIR / "outputs" / "figures" / "correlation_matrix.png")
        st.image(img4, use_column_width=True)
