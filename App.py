#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Converted from Jupyter Notebook: notebook.ipynb
Conversion Date: 2025-12-14T12:02:53.853Z
"""

import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from streamlit_folium import st_folium



st.set_page_config(
    page_title="Pune Food Waste & Donation Routing",
    layout="wide"
)

st.title("🍽️ Pune Food Waste Prediction & Donation Routing")
st.markdown(
    "An AI-powered system to predict food surplus and optimize NGO donation routes in Pune."
)

# ----------------------
# Load Data (Cached)
# ----------------------
@st.cache_data
def load_data():
    restaurants = gpd.read_file("data/restaurants_with_surplus.geojson")
    ngos = gpd.read_file("data/ngos_clustered.geojson")
    routes = pd.read_csv("data/optimized_donation_routes.csv")
    return restaurants, ngos, routes

restaurants, ngos, routes = load_data()

# ----------------------
# Defensive Column Fixes
# ----------------------

# Ensure numeric predicted_surplus
restaurants["predicted_surplus"] = pd.to_numeric(
    restaurants["predicted_surplus"], errors="coerce"
).fillna(0)

# Ensure route distance is numeric
routes["distance_km"] = pd.to_numeric(
    routes["distance_km"], errors="coerce"
)

# Create a safe NGO label column
def get_ngo_label(row):
    return (
        row.get("ngo_name")
        or row.get("name")
        or row.get("registration_clean")
        or "NGO"
    )

ngos["ngo_label"] = ngos.apply(get_ngo_label, axis=1)

# ----------------------
# Sidebar Controls
# ----------------------
st.sidebar.header("Controls")

min_surplus = st.sidebar.slider(
    "Minimum surplus threshold",
    float(restaurants["predicted_surplus"].min()),
    float(restaurants["predicted_surplus"].max()),
    float(restaurants["predicted_surplus"].quantile(0.8))
)

filtered_restaurants = restaurants[
    restaurants["predicted_surplus"] >= min_surplus
]

# ----------------------
# KPIs
# ----------------------
col1, col2, col3 = st.columns(3)

col1.metric(
    "High-Surplus Restaurants",
    int(len(filtered_restaurants))
)

col2.metric(
    "NGOs Covered",
    int(len(ngos))
)

col3.metric(
    "Avg Route Distance (km)",
    round(routes["distance_km"].mean(), 2)
    if len(routes) > 0 else 0
)

# ----------------------
# Map Visualization
# ----------------------
st.subheader("🗺️ Donation Map")

m = folium.Map(
    location=[18.5204, 73.8567],  # Pune
    zoom_start=12,
    tiles="CartoDB positron"
)

# ---- Restaurants ----
for _, row in filtered_restaurants.iterrows():
    if row.geometry is None:
        continue

    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=5,
        color="red",
        fill=True,
        fill_opacity=0.7,
        popup=(
            f"<b>{row.get('name','Restaurant')}</b><br>"
            f"Predicted Surplus: {row['predicted_surplus']:.2f}"
        )
    ).add_to(m)

# ---- NGOs ----
for _, row in ngos.iterrows():
    if row.geometry is None:
        continue

    folium.Marker(
        location=[row.geometry.y, row.geometry.x],
        icon=folium.Icon(color="blue", icon="home"),
        popup=row["ngo_label"]
    ).add_to(m)

# ---- Routes ----
required_route_cols = {
    "geometry_restaurant_x",
    "geometry_restaurant_y",
    "geometry_ngo_x",
    "geometry_ngo_y"
}

if required_route_cols.issubset(routes.columns):
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

# Render map
st_folium(m, width=1200, height=600)

# ----------------------
# Data Table
# ----------------------
st.subheader("📊 Optimized Donation Routes")

st.dataframe(
    routes.sort_values("distance_km").head(25),
    use_container_width=True
)

# ----------------------
# Footer
# ----------------------
st.markdown(
    "---\n"
    "**Built by Ayan Jinabade** | Data Science • GeoSpatial • AI Routing"
)