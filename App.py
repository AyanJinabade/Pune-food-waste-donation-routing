```python
import streamlit as st
import geopandas as gpd
import pandas as pd
import folium

from pathlib import Path
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium


st.set_page_config(
    page_title="Pune Food Waste & Donation Routing",
    layout="wide",
)

st.title("🍽️ Pune Food Waste & Donation Routing")
st.markdown(
    "AI-powered system to predict food surplus and optimize NGO donation routes."
)


@st.cache_data
def load_data():
    base = Path("data")

    def safe_load_geo(path):
        try:
            gdf = gpd.read_file(path)

            if gdf.empty:
                return gdf

            if gdf.crs is None:
                gdf = gdf.set_crs(epsg=4326)

            return gdf.to_crs(epsg=4326)

        except Exception as e:
            st.warning(f"Could not load {path.name}: {e}")
            return gpd.GeoDataFrame()

    def safe_load_csv(path):
        try:
            return pd.read_csv(path)
        except Exception as e:
            st.warning(f"Could not load {path.name}: {e}")
            return pd.DataFrame()

    restaurants = safe_load_geo(
        base / "restaurants_with_surplus.geojson"
    )

    ngos = safe_load_geo(
        base / "ngos_clustered.geojson"
    )

    routes = safe_load_csv(
        base / "optimized_donation_routes.csv"
    )

    return restaurants, ngos, routes


with st.spinner("Loading datasets..."):
    restaurants, ngos, routes = load_data()


@st.cache_data
def preprocess(restaurants, ngos, routes):

    if (
        not restaurants.empty
        and "predicted_surplus" in restaurants.columns
    ):
        restaurants["predicted_surplus"] = pd.to_numeric(
            restaurants["predicted_surplus"],
            errors="coerce",
        ).fillna(0)

    if (
        not routes.empty
        and "distance_km" in routes.columns
    ):
        routes["distance_km"] = pd.to_numeric(
            routes["distance_km"],
            errors="coerce",
        )

    if not ngos.empty:

        def create_label(row):
            if (
                "ngo_name" in ngos.columns
                and pd.notna(row.get("ngo_name"))
            ):
                return row["ngo_name"]

            if (
                "name" in ngos.columns
                and pd.notna(row.get("name"))
            ):
                return row["name"]

            return "NGO"

        ngos["ngo_label"] = ngos.apply(
            create_label,
            axis=1,
        )

    return restaurants, ngos, routes


restaurants, ngos, routes = preprocess(
    restaurants,
    ngos,
    routes,
)


st.sidebar.header("Controls")

if (
    not restaurants.empty
    and "predicted_surplus" in restaurants.columns
):

    min_val = float(
        restaurants["predicted_surplus"].min()
    )

    max_val = float(
        restaurants["predicted_surplus"].max()
    )

    default_val = float(
        restaurants["predicted_surplus"].quantile(0.80)
    )

    if min_val != max_val:
        threshold = st.sidebar.slider(
            "Minimum Surplus Threshold (kg)",
            min_value=min_val,
            max_value=max_val,
            value=default_val,
        )
    else:
        threshold = min_val

    filtered_restaurants = restaurants[
        restaurants["predicted_surplus"]
        >= threshold
    ]

else:
    threshold = 0
    filtered_restaurants = restaurants


col1, col2, col3, col4 = st.columns(4)

total_surplus = (
    filtered_restaurants["predicted_surplus"].sum()
    if (
        not filtered_restaurants.empty
        and "predicted_surplus"
        in filtered_restaurants.columns
    )
    else 0
)

avg_distance = 0

if (
    not routes.empty
    and "distance_km" in routes.columns
):
    avg_distance = round(
        routes["distance_km"].mean(),
        2,
    )

col1.metric(
    "High Surplus Restaurants",
    len(filtered_restaurants),
)

col2.metric(
    "NGOs Covered",
    len(ngos),
)

col3.metric(
    "Avg Route Distance (km)",
    avg_distance,
)

col4.metric(
    "Total Predicted Surplus (kg)",
    round(total_surplus, 2),
)

st.subheader("🗺️ Donation Routing Map")

m = folium.Map(
    location=[18.5204, 73.8567],
    zoom_start=12,
)

restaurant_cluster = MarkerCluster(
    name="Restaurants"
).add_to(m)

ngo_cluster = MarkerCluster(
    name="NGOs"
).add_to(m)


def get_coords(geom):
    try:
        return geom.y, geom.x
    except Exception:
        return None



if not filtered_restaurants.empty:

    for row in filtered_restaurants.itertuples():

        coords = get_coords(row.geometry)

        if coords is None:
            continue

        popup_html = f"""
        <b>Restaurant</b><br>
        Name: {getattr(row, 'name', 'Restaurant')}<br>
        Predicted Surplus:
        {getattr(row, 'predicted_surplus', 0):.2f} kg
        """

        folium.CircleMarker(
            location=coords,
            radius=6,
            color="red",
            fill=True,
            fill_opacity=0.8,
            popup=popup_html,
        ).add_to(restaurant_cluster)


if not ngos.empty:

    for row in ngos.itertuples():

        coords = get_coords(row.geometry)

        if coords is None:
            continue

        folium.Marker(
            location=coords,
            popup=getattr(
                row,
                "ngo_label",
                "NGO",
            ),
            icon=folium.Icon(
                color="blue",
                icon="info-sign",
            ),
        ).add_to(ngo_cluster)


route_cols = [
    "geometry_restaurant_x",
    "geometry_restaurant_y",
    "geometry_ngo_x",
    "geometry_ngo_y",
]

if (
    not routes.empty
    and all(
        col in routes.columns
        for col in route_cols
    )
):

    routes_clean = routes.dropna(
        subset=route_cols
    )

    for row in routes_clean.itertuples():

        folium.PolyLine(
            locations=[
                (
                    row.geometry_restaurant_y,
                    row.geometry_restaurant_x,
                ),
                (
                    row.geometry_ngo_y,
                    row.geometry_ngo_x,
                ),
            ],
            color="green",
            weight=3,
            opacity=0.7,
        ).add_to(m)

folium.LayerControl().add_to(m)


st_folium(
    m,
    use_container_width=True,
    height=650,
)


st.subheader("📊 Optimized Donation Routes")

if not routes.empty:

    if "distance_km" in routes.columns:

        display_df = routes.sort_values(
            "distance_km"
        ).head(25)

    else:
        display_df = routes.head(25)

    st.dataframe(
        display_df,
        use_container_width=True,
    )

else:
    st.info(
        "No route data available."
    )


st.markdown("---")

st.markdown(
    """
### Project Overview

This system helps:

- Predict food surplus from restaurants
- Identify nearby NGOs
- Optimize donation routing
- Reduce food waste
- Improve food redistribution efficiency

**Technologies Used**
- Python
- Streamlit
- GeoPandas
- Folium
- Machine Learning
- Geospatial Analytics
"""
)

st.caption(
    "Built by Ayan Jinabade | Data Analytics & GeoSpatial Intelligence Project"
)
```
