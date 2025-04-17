import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
import streamlit.components.v1 as components

# Load dataset
df = pd.read_excel("Delhi_Streetlights.xlsx")

# Data processing - Calculate area status first
area_stats = df.groupby("Area").agg(
    Total_Lights=("Street Light Number", "count"),
    Working_Lights=("Working", lambda x: (x == 1).sum())
).reset_index()
area_stats["Lighting_Ratio"] = area_stats["Working_Lights"] / area_stats["Total_Lights"]
area_stats["Status"] = ["Well-lit" if ratio >= 0.4 else "Poorly-lit" for ratio in area_stats["Lighting_Ratio"]]

# Merge status back to original dataframe
df = df.merge(area_stats[["Area", "Status"]], on="Area")

# Session state initialization
if 'show_map' not in st.session_state:
    st.session_state.show_map = False
if 'user_location' not in st.session_state:
    st.session_state.user_location = (28.7496585, 77.111702)  # Hardcoded coordinates

# Main UI
st.title("Street Light Status Map")
st.markdown("""
    **Map Legend:**
    - 🟢 Green: Well-lit areas
    - 🔴 Red: Poorly-lit areas
    - 🔵 Blue: Your current location
""")

if st.button("Show Streetlight Map"):
    st.session_state.show_map = True

if st.session_state.show_map:
    # Create map centered on hardcoded location
    m = folium.Map(location=st.session_state.user_location, zoom_start=13)
    
    # Add all individual street light markers
    for _, row in df.iterrows():
        if pd.notnull(row.Latitude) and pd.notnull(row.Longitude):
            color = "green" if row.Status == "Well-lit" else "red"
            folium.CircleMarker(
                location=[row.Latitude, row.Longitude],
                radius=5,  # Smaller radius for better visibility
                color=color,
                fill=True,
                fill_opacity=0.7,
                popup=f"""
                Street Light ID: {row['Street Light Number']}<br>
                Area: {row.Area}<br>
                Status: {row.Status}
                """
            ).add_to(m)
    
    # Add user location marker
    folium.Marker(
        location=st.session_state.user_location,
        popup="Your Current Location",
        icon=folium.Icon(color="blue", icon="user", prefix="fa"),
        draggable=False
    ).add_to(m)
    
    # Display the map
    st_folium(m, width=725)
    
    # Show proximity alerts
    nearest_poor = min(
        [(geodesic(st.session_state.user_location, (row.Latitude, row.Longitude)).meters, row.Area)
         for _, row in df[df.Status == "Poorly-lit"].iterrows()
         if pd.notnull(row.Latitude) and pd.notnull(row.Longitude)],
        key=lambda x: x[0],
        default=None
    )
    
    if nearest_poor and nearest_poor[0] < 1000:
        st.error(f"⚠️ Caution: {nearest_poor[0]:.0f}m from {nearest_poor[1]} (Poorly-lit)")
    else:
        st.success("✅ You're in a well-lit area!")
