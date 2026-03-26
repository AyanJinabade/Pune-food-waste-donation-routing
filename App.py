import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium
from pathlib import Path
from folium.plugins import MarkerCluster

st.set_page_config(
    page_title="Pune Food Waste & Donation Routing",
    layout="wide"
)

st.title("🍽️ Pune Food Waste Prediction & Donation Routing")
st.markdown("AI-powered system to predict food surplus and optimize NGO routes.")

@st.cache_data
def load_data():
    base = Path("data")

    def safe_load_geo(path):
        try:
            gdf = gpd.read_file(path)
            return gdf.to_crs(epsg=4326) if gdf.crs else gdf.set_crs(epsg=4326)
        except:
            return gpd.GeoDataFrame()

    def safe_load_csv(path):
        try:
            return pd.read_csv(path)
        except:
            return pd.DataFrame()

    return (
        safe_load_geo(base / "restaurants_with_surplus.geojson"),
        safe_load_geo(base / "ngos_clustered.geojson"),
        safe_load_csv(base / "optimized_donation_routes.csv")
    )

with st.spinner("Loading data..."):
    restaurants, ngos, routes = load_data()

@st.cache_data
def preprocess(restaurants, ngos, routes):

    if "predicted_surplus" in restaurants.columns:
        restaurants["predicted_surplus"] = pd.to_numeric(
            restaurants["predicted_surplus"], errors="coerce"
        ).fillna(0)

    if "distance_km" in routes.columns:
        routes["distance_km"] = pd.to_numeric(routes["distance_km"], errors="coerce")

    if not ngos.empty:
        ngos["ngo_label"] = ngos.apply(
            lambda r: r.get("ngo_name") or r.get("name") or "NGO",
            axis=1
        )

    return restaurants, ngos, routes

restaurants, ngos, routes = preprocess(restaurants, ngos, routes)
st.sidebar.header("Controls")

if not restaurants.empty and "predicted_surplus" in restaurants.columns:

    min_val = float(restaurants["predicted_surplus"].min())
    max_val = float(restaurants["predicted_surplus"].max())

    threshold = st.sidebar.slider(
        "Minimum surplus threshold",
        min_val,
        max_val,
        float(restaurants["predicted_surplus"].quantile(0.8))
    ) if min_val != max_val else min_val

    filtered_restaurants = restaurants[
        restaurants["predicted_surplus"] >= threshold
    ]

else:
    st.warning("No restaurant data available.")
    filtered_restaurants = restaurants

col1, col2, col3 = st.columns(3)

col1.metric("High-Surplus Restaurants", len(filtered_restaurants))
col2.metric("NGOs Covered", len(ngos))

avg_dist = (
    round(routes["distance_km"].mean(), 2)
    if "distance_km" in routes.columns and not routes.empty
    else 0
)

col3.metric("Avg Route Distance (km)", avg_dist)

st.subheader("🗺️ Donation Map")

m = folium.Map(location=[18.5204, 73.8567], zoom_start=12)

restaurant_cluster = MarkerCluster().add_to(m)
ngo_cluster = MarkerCluster().add_to(m)

def get_coords(geom):
    try:
        return geom.y, geom.x
    except:
        return None

for row in filtered_restaurants.itertuples():
    coords = get_coords(row.geometry)
    if not coords:
        continue

    folium.CircleMarker(
        location=coords,
        radius=5,
        color="red",
        fill=True,
        fill_opacity=0.7,
        popup=f"{getattr(row, 'name', 'Restaurant')} | Surplus: {getattr(row, 'predicted_surplus', 0):.2f}"
    ).add_to(restaurant_cluster)

# NGOs
for row in ngos.itertuples():
    coords = get_coords(row.geometry)
    if not coords:
        continue

    folium.Marker(
        location=coords,
        icon=folium.Icon(color="blue"),
        popup=getattr(row, "ngo_label", "NGO")
    ).add_to(ngo_cluster)

# Routes
route_cols = [
    "geometry_restaurant_x", "geometry_restaurant_y",
    "geometry_ngo_x", "geometry_ngo_y"
]

if all(col in routes.columns for col in route_cols):

    routes_clean = routes.dropna(subset=route_cols)

    for row in routes_clean.itertuples():
        folium.PolyLine(
            locations=[
                (row.geometry_restaurant_y, row.geometry_restaurant_x),
                (row.geometry_ngo_y, row.geometry_ngo_x)
            ],
            color="green",
            weight=2,
            opacity=0.6
        ).add_to(m)

# Render map
st_folium(m, use_container_width=True, height=600)

st.subheader("📊 Optimized Donation Routes")

if not routes.empty:
    if "distance_km" in routes.columns:
        st.dataframe(routes.sort_values("distance_km").head(25))
    else:
        st.dataframe(routes.head(25))
else:
    st.info("No route data available.")

st.markdown(
    "---\n"
    "**Built by Ayan Jinabade** | Data Science • GeoSpatial • AI Routing"
)
