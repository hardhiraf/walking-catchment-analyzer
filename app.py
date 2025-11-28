import streamlit as st
import folium
from folium.features import DivIcon
from streamlit_folium import st_folium
import osmnx as ox
import networkx as nx
import pandas as pd
import geopandas as gpd
import altair as alt

# --- 1. CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Walking Catchment Analyzer")


# --- FUNCTIONS (Cached) ---
@st.cache_data
def get_amenities(_polygon, tags, lat, lon):
    try:
        pois = ox.features_from_polygon(_polygon, tags=tags)
        return pois
    except Exception:
        return None


@st.cache_data
def calculate_isochrone_network(lat, lon, walk_time_min, speed_kph=4.5):
    dist = (walk_time_min / 60) * speed_kph * 1000 * 1.2
    G = ox.graph_from_point((lat, lon), dist=dist, network_type="walk")

    center_node = ox.distance.nearest_nodes(G, lon, lat)
    G = ox.project_graph(G)
    meters_per_minute = speed_kph * 1000 / 60

    for u, v, k, data in G.edges(keys=True, data=True):
        data["time"] = data["length"] / meters_per_minute

    subgraph = nx.ego_graph(G, center_node, radius=walk_time_min, distance="time")
    nodes_gdf, edges_gdf = ox.graph_to_gdfs(subgraph)

    nodes_gdf = nodes_gdf.to_crs(epsg=4326)
    edges_gdf = edges_gdf.to_crs(epsg=4326)

    # Union all nodes to create the polygon hull
    query_polygon = nodes_gdf.union_all().convex_hull

    return edges_gdf, query_polygon


# --- 2. SESSION STATE ---
if "click_coords" not in st.session_state:
    st.session_state["click_coords"] = None
if "analysis_results" not in st.session_state:
    st.session_state["analysis_results"] = None
if "trigger_calc" not in st.session_state:
    st.session_state["trigger_calc"] = False

# --- 3. GLOBAL VARIABLES ---
color_map = {
    "Office": "#7F8C8D",
    "Healthcare": "#C0392B",
    "Transit (Train/Rail)": "#8E44AD",
    "Transit (Bus/Other)": "#F39C12",
    "Shop": "#E84393",
    "Leisure/Sport": "#27AE60",
    "Tourism": "#D35400",
    "Education": "#F1C40F",
    "Worship": "#9B59B6",
    "Grocery": "#2ECC71",
    "Others": "#16A085",
}

# --- 4. PREPARE DATA ---
res = st.session_state["analysis_results"]
has_data = False
pois_data = pd.DataFrame()
walk_time = 10

if res and res["coords"] == st.session_state["click_coords"]:
    has_data = True
    raw_pois = res["pois"]
    if raw_pois is not None and not raw_pois.empty:

        def classify_poi(row):
            amenity = row.get("amenity")
            shop = row.get("shop")
            railway = row.get("railway")
            
            if pd.notna(railway): return "Transit (Train/Rail)"
            if pd.notna(row.get("public_transport")) or row.get("highway") == "bus_stop": return "Transit (Bus/Other)"
            
            if amenity in ['school', 'university', 'college', 'kindergarten', 'language_school']:
                return "Education"
            if amenity == 'place_of_worship':
                return "Worship"
            if amenity in ['clinic', 'hospital', 'pharmacy', 'doctors', 'dentist']:
                return "Healthcare"
            if pd.notna(row.get("healthcare")): return "Healthcare"
            
            if shop in ['supermarket', 'convenience', 'greengrocer', 'bakery', 'market']:
                return "Grocery"
            
            if pd.notna(row.get("leisure")) or pd.notna(row.get("sport")): return "Leisure/Sport"
            if pd.notna(row.get("tourism")): return "Tourism"
            if pd.notna(row.get("office")): return "Office"
            
            return "Others"

        raw_pois["main_category"] = raw_pois.apply(classify_poi, axis=1)
        raw_pois["display_name"] = raw_pois["main_category"] + ": " + raw_pois["amenity"].fillna("Location")
        pois_data = raw_pois

# --- 5. SIDEBAR ---
with st.sidebar:
    st.header("Settings")
    walk_time = st.slider("Walking Time (minutes) at 4.5 km/h", 1, 15, 10)

    st.divider()
    st.header("Filters")

    if has_data and not pois_data.empty:
        available_cats = sorted(pois_data["main_category"].unique().astype(str))
        
        # --- SELECT/DESELECT BUTTONS ---
        col1, col2 = st.columns(2)
        if col1.button("Select All", use_container_width=True):
            st.session_state["selected_layers"] = available_cats
            st.rerun()
        
        if col2.button("Deselect All", use_container_width=True):
            st.session_state["selected_layers"] = []
            st.rerun()

        # The Widget
        # key="selected_layers" connects this widget to session state
        selected_layers = st.pills(
            "Toggle Categories:",
            options=available_cats,
            default=available_cats, # Default to all if no state exists
            selection_mode="multi",
            key="selected_layers" 
        )
    else:
        st.info("Filters will appear after the analysis is complete.")
        selected_layers = []

# --- 6. MAIN LAYOUT ---
st.title("Walking Catchment Analyzer")

col_map, col_dash = st.columns([3, 2])

# --- RIGHT COLUMN (DASHBOARD) ---
with col_dash:
    
    if st.session_state["click_coords"] and not has_data:
        st.subheader("📍 Location Selected")
        st.info(f"Coordinates: {st.session_state['click_coords'][0]:.4f}, {st.session_state['click_coords'][1]:.4f}")
        st.markdown("Click the button below to generate the isochrone.")
        if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
            st.session_state["trigger_calc"] = True 
            st.rerun()

    elif has_data:
        st.subheader("📊 Amenities Breakdown")

        if not pois_data.empty:
            # Filter Data
            chart_source = pois_data[pois_data["main_category"].isin(selected_layers)]

            if not chart_source.empty:
                chart_agg = chart_source["main_category"].value_counts().reset_index()
                chart_agg.columns = ["Category", "Count"]

                base = alt.Chart(chart_agg).encode(
                    y=alt.Y("Category", sort="-x", title=None),
                    tooltip=["Category", "Count"],
                )
                bars = base.mark_bar().encode(
                    x=alt.X("Count", title="Count"),
                    color=alt.Color(
                        "Category",
                        scale=alt.Scale(
                            domain=list(color_map.keys()), range=list(color_map.values())
                        ),
                        legend=None,
                    ),
                )
                text = base.mark_text(dx=5, align="left", color="#FFFFFF").encode(
                    x=alt.X("Count"), text="Count"
                )
                final_chart = (bars + text).properties(height=350)
                st.altair_chart(final_chart, width="stretch")
            else:
                st.warning("No categories selected. Click 'Select All' in the sidebar.")
        else:
            st.warning("No amenities found in this range.")

        st.divider()
        st.subheader("📏 Catchment Statistics")
        total_length_km = res["edges"]["length"].sum() / 1000
        
        poly_gdf = gpd.GeoDataFrame(geometry=[res["polygon"]], crs="EPSG:4326")
        poly_utm = poly_gdf.to_crs(poly_gdf.estimate_utm_crs())
        area_sq_km = poly_utm.area[0] / 1e6 
        
        m1, m2 = st.columns(2)
        m1.metric("Isochrone Area", f"{area_sq_km:.2f} km²")
        m2.metric("Street Network Length", f"{total_length_km:.2f} km")

    else:
        st.markdown(
            """
            <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center; color: #555;">
                <h4>Ready to Analyze</h4>
                <p>Click anywhere on the map to place a Start Point.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

# --- LEFT COLUMN (MAP) ---
with col_map:
    if st.session_state["click_coords"]:
        map_center = st.session_state["click_coords"]
    else:
        map_center = [-6.1754, 106.8272]

    m = folium.Map(location=map_center, zoom_start=15, tiles=None)

    folium.TileLayer(tiles="OpenStreetMap", name="Street Map", control=True).add_to(m)
    folium.TileLayer(tiles="CartoDB positron", name="Light Map", control=True).add_to(m)
    folium.TileLayer(tiles="CartoDB dark_matter", name="Dark Map", control=True).add_to(m)
    

    if st.session_state["click_coords"]:
        clat, clon = st.session_state["click_coords"]
        folium.Marker(
            location=[clat, clon],
            icon=DivIcon(
                icon_size=(20, 20),
                icon_anchor=(10, 10),
                html="""
                <div style="
                    width: 20px; height: 20px; background-color: #E74C3C; 
                    border: 2px solid black; transform: rotate(45deg); 
                    box-shadow: 2px 2px 4px rgba(0,0,0,0.4);">
                </div>
                """,
            ),
            popup="Start Point",
        ).add_to(m)

    if has_data:
        folium.GeoJson(
            res["polygon"],
            style_function=lambda x: {"fillColor": "#3498DB", "color": "#3498DB", "weight": 1, "fillOpacity": 0.15},
            name="Catchment Area",
        ).add_to(m)

        folium.GeoJson(
            res["edges"],
            style_function=lambda x: {"color": "#3498DB", "weight": 2, "opacity": 0.8},
            name="Walking Network",
        ).add_to(m)

        if not pois_data.empty:
            fg = folium.FeatureGroup(name="Amenities")
            final_filtered_data = pois_data[pois_data["main_category"].isin(selected_layers)]
            for idx, row in final_filtered_data.iterrows():
                if row.geometry.geom_type == "Point":
                    loc = [row.geometry.y, row.geometry.x]
                else:
                    loc = [row.geometry.centroid.y, row.geometry.centroid.x]
                cat = row["main_category"]
                color = color_map.get(cat, "gray")
                radius = 7 if "Train" in cat else 5
                folium.CircleMarker(loc, radius=radius, color=color, weight=0.5, fill=True, fill_color=color, fill_opacity=1, popup=row["display_name"]).add_to(fg)
            fg.add_to(m)

    folium.LayerControl(position="topright").add_to(m)
    
    output = st_folium(m, height=700, width=None, returned_objects=["last_clicked"])

    if output["last_clicked"]:
        new_lat = output["last_clicked"]["lat"]
        new_lon = output["last_clicked"]["lng"]
        if st.session_state["click_coords"] != (new_lat, new_lon):
            st.session_state["click_coords"] = (new_lat, new_lon)
            st.session_state["analysis_results"] = None 
            st.rerun()

    if st.session_state.get("trigger_calc", False):
        lat, lon = st.session_state["click_coords"]
        st.session_state["trigger_calc"] = False 
        
        with st.status("⏳ Analyzing urban network...", expanded=True) as status:
            try:
                st.write("Tracing street network...")
                edges_gdf, query_poly = calculate_isochrone_network(lat, lon, walk_time)
                st.write("Scanning amenities...")
                tags = {
                    "amenity": True, "shop": True, "office": True,
                    "leisure": True, "healthcare": True, "sport": True,
                    "public_transport": True, "highway": "bus_stop",
                    "railway": ["station", "halt", "subway_entrance"],
                    "tourism": True,
                }
                pois = get_amenities(query_poly, tags, lat, lon)
                
                if pois is not None and not pois.empty:
                    pois = pois[pois.geometry.centroid.within(query_poly)]
                    
                    # --- CRITICAL FIX ---
                    # When a new analysis finishes, FORCE the session state key for filters to be removed.
                    # This forces Streamlit to re-initialize the widget using the 'default' (which is All Categories).
                    if "selected_layers" in st.session_state:
                        del st.session_state["selected_layers"]

                st.session_state["analysis_results"] = {
                    "coords": (lat, lon), "walk_time": walk_time, "edges": edges_gdf, "pois": pois, "polygon": query_poly
                }
                status.update(label="✅ Complete!", state="complete", expanded=False)
                st.rerun()
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                status.update(label="❌ Failed", state="error")
