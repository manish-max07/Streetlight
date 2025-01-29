import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic
import streamlit.components.v1 as components

# Load dataset
df = pd.read_excel("Delhi_Streetlights.xlsx")

# Data processing
df_merged = df.groupby("Area").agg(
    Total_Lights=("Street Light Number", "count"),
    Working_Lights=("Working", lambda x: (x == 1).sum()),
    Flickering_Lights=("Flickering", lambda x: (x == 1).sum()),
    Latitude=("Latitude", "mean"),
    Longitude=("Longitude", "mean")
).reset_index()
df_merged["Status"] = ["Well-lit" if (w/t) >= 0.4 else "Poorly-lit" 
                      for w, t in zip(df_merged["Working_Lights"], df_merged["Total_Lights"])]

# Session state initialization
if 'show_map' not in st.session_state:
    st.session_state.show_map = False
if 'user_location' not in st.session_state:
    st.session_state.user_location = None

# Main UI
st.title("Street Light Status Map")

# Add permanent message handler component
components.html("""
<script>
window.addEventListener("message", (event) => {
    if (event.data.isStreamlitMessage && event.data.type === 'setComponentValue') {
        window.parent.postMessage({
            isStreamlitMessage: true,
            type: 'setComponentValue',
            componentValue: event.data.componentValue
        }, "*");
    }
});
</script>
""", height=0)

# Single button implementation
if st.button("Show Streetlight Map"):
    # Request location and trigger map show
    components.html("""
    <script>
    navigator.geolocation.getCurrentPosition(
        position => {
            window.parent.postMessage({
                isStreamlitMessage: true,
                type: 'setComponentValue',
                componentValue: {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude,
                    show_map: true
                }
            }, "*");
        },
        error => {
            window.parent.postMessage({
                isStreamlitMessage: true,
                type: 'setComponentValue',
                componentValue: {
                    show_map: true,
                    error: "Location access denied"
                }
            }, "*");
        }
    );
    </script>
    """, height=0)

# Handle incoming location data
if 'componentValue' in st.session_state:
    data = st.session_state.componentValue
    
    if data and 'show_map' in data:
        st.session_state.show_map = True
        if 'lat' in data and 'lng' in data:
            st.session_state.user_location = (data['lat'], data['lng'])
        else:
            st.session_state.user_location = None
    del st.session_state.componentValue

# Display the map when authorized
if st.session_state.show_map:
    # Create map with appropriate center
    if st.session_state.user_location:
        map_center = st.session_state.user_location
        zoom = 13
    else:
        map_center = [28.6139, 77.2090]  # Default Delhi coordinates
        zoom = 11
    
    m = folium.Map(location=map_center, zoom_start=zoom)
    
    # Add street light markers
    for _, row in df_merged.iterrows():
        folium.CircleMarker(
            location=[row.Latitude, row.Longitude],
            radius=8,
            color="green" if row.Status == "Well-lit" else "red",
            fill=True,
            popup=f"{row.Area}<br>{row.Status}"
        ).add_to(m)
    
    # Add user location if available
    if st.session_state.user_location:
        folium.Marker(
            location=st.session_state.user_location,
            popup="Your Location",
            icon=folium.Icon(color="blue", icon="user", prefix="fa")
        ).add_to(m)
    
    # Display the map
    map_data = st_folium(m, width=725, key="main_map")
    
    # Show proximity alerts if location available
    if st.session_state.user_location:
        nearest_poor = min(
            [(geodesic(st.session_state.user_location, 
                      (row.Latitude, row.Longitude)).meters, row.Area)
             for _, row in df_merged[df_merged.Status == "Poorly-lit"].iterrows()],
            key=lambda x: x[0],
            default=None
        )
        
        if nearest_poor and nearest_poor[0] < 1000:
            st.error(f"⚠️ Caution: {nearest_poor[0]:.0f}m from {nearest_poor[1]} (Poorly-lit)")
        else:
            st.success("✅ You're in a well-lit area!")