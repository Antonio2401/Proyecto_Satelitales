import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import plotly.express as px
import os

# === CONFIGURACIÓN GENERAL ===
st.set_page_config(page_title="Monitoreo Calidad del Aire", layout="wide", page_icon="🌫️")

# === CARGA DE DATOS ===
historico_co = pd.read_csv("Historico20192024CO.csv")
historico_no2 = pd.read_csv("Historico20192024NO2.csv")
pred_co = pd.read_csv("Predicciones_CO_2025_2029.csv")
pred_no2 = pd.read_csv("Predicciones_NO2_2025_2029.csv")

# === UNIFICACIÓN DE DATOS ===
co_historico = historico_co[["anio", "zona", "co_mg_m3_suelo"]].rename(columns={"co_mg_m3_suelo": "valor"})
co_pred = pred_co[["anio", "zona", "co_mg_m3_suelo_pred"]].rename(columns={"co_mg_m3_suelo_pred": "valor"})
co = pd.concat([co_historico, co_pred])
co["contaminante"] = "CO"

no2_historico = historico_no2[["anio", "zona", "no2_ug_m3_suelo"]].rename(columns={"no2_ug_m3_suelo": "valor"})
no2_pred = pred_no2[["anio", "zona", "no2_ug_m3_suelo_pred"]].rename(columns={"no2_ug_m3_suelo_pred": "valor"})
no2 = pd.concat([no2_historico, no2_pred])
no2["contaminante"] = "NO2"

df_total = pd.concat([co, no2])
df_total["zona"] = df_total["zona"].replace({
    "Dist_26Oct": "26 de Octubre",
    "Dist_Paita": "Paita",
    "Parinas": "Pariñas"
})

# === SIDEBAR ===
st.sidebar.header("⚙️ Parámetros de Visualización")
opcion = st.sidebar.selectbox("📌 Seleccione sección:", ["📈 Análisis", "🗺️ Mapa"])
modo = st.sidebar.radio("🌓 Modo:", ["🌞 Claro", "🌙 Oscuro"])

if modo == "🌞 Claro":
    st.markdown("<style>.main { background-color: #ffffff; color: #000000; }</style>", unsafe_allow_html=True)
else:
    st.markdown("<style>.main { background-color: #0e1117; color: #f5f5f5; }</style>", unsafe_allow_html=True)

st.title("🌎 Sistema de Monitoreo de Calidad del Aire - Piura")

# === MAPA ===
if opcion == "🗺️ Mapa":
    st.subheader("🗺️ Zonas de Análisis Satelital")

    geojson_path = os.path.join(os.getcwd(), "zonas_piura.geojson")
    gdf = gpd.read_file(geojson_path)

    zona_sel = st.selectbox("📍 Seleccione zona:", gdf["Zona"].unique())
    zona_filt = gdf[gdf["Zona"] == zona_sel]
    centro = zona_filt.geometry.unary_union.centroid

    m = folium.Map(location=[centro.y, centro.x], zoom_start=12, tiles="CartoDB positron")

    folium.GeoJson(
        gdf,
        style_function=lambda x: {"fillColor": "gray", "color": "gray", "weight": 1, "fillOpacity": 0.1}
    ).add_to(m)

    folium.GeoJson(
        zona_filt,
        style_function=lambda x: {"fillColor": "#ff6600", "color": "red", "weight": 3, "fillOpacity": 0.5},
        tooltip=folium.GeoJsonTooltip(fields=["Zona"])
    ).add_to(m)

    st_folium(m, width=700, height=500)

# === ANÁLISIS DE CONTAMINANTES ===
elif opcion == "📈 Análisis":
    zona = st.sidebar.selectbox("📍 Zona:", df_total["zona"].unique())
    contaminante = st.sidebar.selectbox("☁️ Contaminante:", ["NO2", "CO"])
    rango_anios = st.sidebar.slider("📅 Rango de Años:", 2019, 2029, (2024, 2025))

    # === FILTRADO Y AGRUPACIÓN PROMEDIADA ===
    df_zc = df_total[
        (df_total["zona"] == zona) &
        (df_total["contaminante"] == contaminante) &
        (df_total["anio"].between(rango_anios[0], rango_anios[1]))
    ].groupby("anio").agg({"valor": "mean"}).reset_index()

    # === GRÁFICO LINEAL ===
    st.subheader(f"📈 Evolución Promedio Anual de {contaminante} en {zona} ({rango_anios[0]}–{rango_anios[1]})")
    fig = px.line(df_zc, x="anio", y="valor", markers=True,
                  title=f"{contaminante} - {zona} ({rango_anios[0]}–{rango_anios[1]})")
    fig.add_hline(
        y=10 if contaminante == "NO2" else 4,
        line_dash="dash",
        line_color="red",
        annotation_text="Límite OMS",
        annotation_position="top left"
    )
    st.plotly_chart(fig, use_container_width=True)

    # === ALERTAS POR AÑO ===
    limite = 10 if contaminante == "NO2" else 4
    for _, fila in df_zc.iterrows():
        anio, valor = int(fila["anio"]), fila["valor"]
        if valor > limite:
            st.error(f"⚠️ En {anio}, la concentración promedio fue **{valor:.2f}**, superando el límite de la OMS.")
        else:
            st.success(f"✅ En {anio}, la concentración promedio fue **{valor:.2f}**, dentro del límite permitido.")

    # === TABLA DE DATOS ===
    st.markdown("### 📄 Datos promediados por año")
    st.dataframe(df_zc, use_container_width=True)

    # === BOTÓN DE EXPORTACIÓN ===
    csv = df_zc.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Descargar CSV", csv, f"{zona}_{contaminante}_rango_{rango_anios[0]}_{rango_anios[1]}.csv", "text/csv")
