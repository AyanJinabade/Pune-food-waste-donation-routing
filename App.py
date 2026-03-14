
import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
from pathlib import Path


# Page Config

st.set_page_config(
    page_title="Pune Food Waste & Donation Routing",
    layout="wide"
)

st.title("🍽️ Pune Food Waste Prediction & Donation Routing")
st.markdown(
    "AI-powered system to predict food surplus and optimize NGO donation routes in Pune."
)


# Load Data (Cached)
@st.cache_data
def load_data():

    base = Path("data")

    try:
        restaurants = gpd.read_file(base / "restaurants_with_surplus.geojson")
    except:
        restaurants = gpd.GeoDataFrame()

    try:
        ngos = gpd.read_file(base / "ngos_clustered.geojson")
    except:
        ngos = gpd.GeoDataFrame()

    try:
        routes = pd.read_csv(base / "optimized_donation_routes.csv")
    except:
        routes = pd.DataFrame()

    return restaurants, ngos, routes


restaurants, ngos, routes = load_data()

# Data Cleaning

if "predicted_surplus" in restaurants.columns:
    restaurants["predicted_surplus"] = pd.to_numeric(
        restaurants["predicted_surplus"], errors="coerce"
    ).fillna(0)

if "distance_km" in routes.columns:
    routes["distance_km"] = pd.to_numeric(
        routes["distance_km"], errors="coerce"
    )

# NGO label safety
def get_ngo_label(row):
    return (
        row.get("ngo_name")
        or row.get("name")
        or row.get("registration_clean")
        or "NGO"
    )

if not ngos.empty:
    ngos["ngo_label"] = ngos.apply(get_ngo_label, axis=1)

# Sidebar Controls
st.sidebar.header("Controls")

if not restaurants.empty:

    min_surplus = st.sidebar.slider(
        "Minimum surplus threshold",
        float(restaurants["predicted_surplus"].min()),
        float(restaurants["predicted_surplus"].max()),
        float(restaurants["predicted_surplus"].quantile(0.8))
    )

    filtered_restaurants = restaurants[
        restaurants["predicted_surplus"] >= min_surplus
    ]

else:
    filtered_restaurants = restaurants


# KPI Section
col1, col2, col3 = st.columns(3)

col1.metric(
    "High-Surplus Restaurants",
    int(len(filtered_restaurants))
)

col2.metric(
    "NGOs Covered",
    int(len(ngos))
)

if "distance_km" in routes.columns and len(routes) > 0:
    avg_dist = round(routes["distance_km"].mean(), 2)
else:
    avg_dist = 0

col3.metric("Avg Route Distance (km)", avg_dist)

# Map Visualization
st.subheader("🗺️ Donation Map")

m = folium.Map(
    location=[18.5204, 73.8567],  # Pune
    zoom_start=12,
    tiles="CartoDB positron"
)

# Restaurants
for _, row in filtered_restaurants.iterrows():

    if row.geometry is None:
        continue

    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=6,
        color="red",
        fill=True,
        fill_opacity=0.7,
        popup=f"""
        <b>{row.get('name','Restaurant')}</b><br>
        Surplus: {row.get('predicted_surplus',0):.2f}
        """
    ).add_to(m)

# NGOs
for _, row in ngos.iterrows():

    if row.geometry is None:
        continue

    folium.Marker(
        location=[row.geometry.y, row.geometry.x],
        icon=folium.Icon(color="blue", icon="home"),
        popup=row.get("ngo_label", "NGO")
    ).add_to(m)

# Routes
route_cols = [
    "geometry_restaurant_x",
    "geometry_restaurant_y",
    "geometry_ngo_x",
    "geometry_ngo_y"
]

if all(col in routes.columns for col in route_cols):

    for _, row in routes.iterrows():

        folium.PolyLine(
            locations=[
                (row["geometry_restaurant_y"], row["geometry_restaurant_x"]),
                (row["geometry_ngo_y"], row["geometry_ngo_x"])
            ],
            color="green",
            weight=2,
            opacity=0.6
        ).add_to(m)

# Display map
st_folium(m, width=1200, height=600)


# Routes Table
st.subheader("📊 Optimized Donation Routes")

if "distance_km" in routes.columns:

    st.dataframe(
        routes.sort_values("distance_km").head(25),
        use_container_width=True
    )

else:

    st.dataframe(routes.head(25), use_container_width=True)

# Footer
st.markdown(
    "---\n"
    "**Built by Ayan Jinabade** | Data Science • GeoSpatial • AI Routing"
)
