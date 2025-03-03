import os
import streamlit as st
import pandas as pd
import plotly.express as px
from rapidfuzz import process, fuzz
import pycountry

# 📌 Cargar los datos de calidad del aire
@st.cache_data
def load_air_quality_data():
    df = pd.read_csv("global_air_pollution_data.csv")
    
    # Renombrar columnas clave
    df = df.rename(columns={
        "country_name": "Country",
        "city_name": "City",
        "aqi_value": "AQI",
        "pm2.5_aqi_value": "PM2.5",
        "no2_aqi_value": "NO2",
        "ozone_aqi_value": "Ozone"
    })
    
    # Mantener solo las columnas necesarias
    df = df[["Country", "City", "AQI", "PM2.5", "NO2", "Ozone"]]
    
    # Normalizar nombres de ciudades y países
    df["City"] = df["City"].str.lower().str.replace("[^a-z0-9]", "", regex=True)
    df["Country"] = df["Country"].apply(lambda x: pycountry.countries.lookup(x).alpha_2 if x in pycountry.countries else x)
    
    return df

# 📌 Cargar y limpiar los datos de coordenadas de ciudades
@st.cache_data
def load_city_coordinates():
    df_geo = pd.read_csv("geonames_cleaned.csv", low_memory=False)
    
    # Renombrar columnas clave
    df_geo = df_geo.rename(columns={
        "name": "City",
        "country_code": "Country",
        "latitude": "lat",
        "longitude": "lon"
    })
    
    # Mantener solo columnas clave
    df_geo = df_geo[["City", "Country", "lat", "lon"]]
    
    # Normalizar nombres de ciudades
    df_geo["City"] = df_geo["City"].str.lower().str.replace("[^a-z0-9]", "", regex=True)
    
    return df_geo

# 📌 Cargar y unir los datos
df_air_quality = load_air_quality_data()
df_coordinates = load_city_coordinates()

if not df_coordinates.empty:
    # Aplicar Fuzzy Matching para mejorar la coincidencia de ciudades
    city_mapping = {}
    for city in df_air_quality["City"].unique():
        match, score, _ = process.extractOne(city, df_coordinates["City"].unique(), scorer=fuzz.ratio)
        if score > 85:
            city_mapping[city] = match

    df_air_quality["City"] = df_air_quality["City"].replace(city_mapping)

    # Unir dataset de calidad del aire con coordenadas de GeoNames
    df_final = df_air_quality.merge(df_coordinates, on=["City", "Country"], how="left")

    # Filtrar ciudades con coordenadas nulas
    df_final = df_final.dropna(subset=['lat', 'lon'])

# 📌 Configurar Streamlit
st.set_page_config(page_title="Global Air Quality Dashboard", page_icon="🌍", layout="wide")
st.title("🌍 Global Air Quality Dashboard")

st.markdown("""
This dashboard visualizes air quality data across different cities and time periods.
Monitor various pollutants including PM2.5, NO2, and Ozone.
""")

# 🌍 Mapa Global de Calidad del Aire
st.subheader("Global Air Quality Map")
st.caption("Click on any point in the map to select a country")

fig_map = px.scatter_mapbox(
    df_final,
    lat='lat',
    lon='lon',
    color='AQI',
    size='PM2.5',
    hover_name='City',
    hover_data=['PM2.5', 'NO2', 'Ozone', 'AQI', 'Country'],
    color_continuous_scale="Viridis",
    zoom=2,
    title="Air Quality Index Across Cities",
    size_max=20
)

fig_map.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 30, "l": 0, "b": 0}, height=500)
st.plotly_chart(fig_map, use_container_width=True)

# 📌 Filtros de país y ciudad
countries = sorted(df_final['Country'].dropna().unique())
selected_country = st.sidebar.selectbox("Select Country", countries)
cities_in_country = sorted(df_final[df_final['Country'] == selected_country]['City'].unique())
selected_city = st.sidebar.selectbox("Select City", cities_in_country)

# 📌 Mostrar métricas del país
st.subheader(f"🌎 Country Overview: {selected_country}")
country_data = df_final[df_final['Country'] == selected_country]

avg_country_pm25 = country_data['PM2.5'].mean()
avg_country_no2 = country_data['NO2'].mean()
avg_country_aqi = country_data['AQI'].mean()

col1, col2, col3 = st.columns(3)
col1.metric("PM2.5", f"{avg_country_pm25:.2f} µg/m³", "🌫️")
col2.metric("NO2", f"{avg_country_no2:.2f} ppb", "🌬️")
col3.metric("AQI", f"{avg_country_aqi:.2f}", "🔥")

# 📌 Gráfico de tendencias para la ciudad seleccionada
st.subheader(f"Air Quality Trends in {selected_city}")
city_data = df_final[df_final['City'] == selected_city]
pollutants = ['PM2.5', 'NO2']
selected_pollutant = st.selectbox("Select Pollutant", pollutants)

fig = px.line(city_data, x='AQI', y=selected_pollutant, markers=True, title=f"{selected_pollutant} Levels in {selected_city}", labels={'AQI': 'Date', selected_pollutant: f"{selected_pollutant} (µg/m³)"})

fig.update_layout(xaxis_title="Date", yaxis_title=f"{selected_pollutant} Concentration", template="plotly_white")
st.plotly_chart(fig, use_container_width=True)

