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
st.markdown("""
    **Map Legend:**
    - 🟢 Green: Well-lit areas
    - 🔴 Red: Poorly-lit areas
    - 🔵 Blue: Your current location
""")

# Improved geolocation component
def get_geolocation():
    return components.declare_component(
        "geolocation",
        url="https://delhi-streetlight-map.streamlit.app",  # Uses iframe-relay for direct communication
    )

# Single button implementation
if st.button("Show Streetlight Map"):
    # Request location using improved component
    st.session_state.user_location = (28.666169, 77.302454)  # Hardcoded coordinates
    st.session_state.show_map = True
    
    # if location_data and 'latitude' in location_data and 'longitude' in location_data:
    #     st.session_state.user_location = (location_data['latitude'], location_data['longitude'])
    #     st.session_state.show_map = True
    # else:
    #     st.session_state.show_map = True
    #     st.session_state.user_location = None

# Alternative reliable JavaScript implementation
components.html("""
<script>
// Direct communication channel
window.addEventListener('load', function() {
    navigator.geolocation.getCurrentPosition(function(position) {
        window.parent.postMessage({
            type: 'currentLocation',
            latitude: position.coords.latitude,
            longitude: position.coords.longitude
        }, '*');
    }, function(error) {
        window.parent.postMessage({
            type: 'locationError',
            error: error.message
        }, '*');
    });
});

// Listen for Streamlit messages
window.addEventListener('message', function(event) {
    if (event.data.type === 'requestLocation') {
        navigator.geolocation.getCurrentPosition(function(position) {
            window.parent.postMessage({
                type: 'currentLocation',
                latitude: position.coords.latitude,
                longitude: position.coords.longitude
            }, '*');
        });
    }
});
</script>
""", height=0)

# Handle incoming location data
if 'currentLocation' in st.session_state:
    loc = st.session_state.currentLocation
    st.session_state.user_location = (loc['latitude'], loc['longitude'])
    st.session_state.show_map = True
    del st.session_state.currentLocation

# Display the map
if st.session_state.show_map:
    # Create map with appropriate center
    if st.session_state.user_location:
        map_center = st.session_state.user_location
        zoom = 13
    else:
        map_center = [28.6139, 77.2090]  # Default Delhi coordinates
        zoom = 11
    
    m = folium.Map(location=map_center, zoom_start=zoom, control_scale=True)
    
    # Add street light markers
    for _, row in df_merged.iterrows():
        folium.CircleMarker(
            location=[row.Latitude, row.Longitude],
            radius=8,
            color="green" if row.Status == "Well-lit" else "red",
            fill=True,
            fill_opacity=0.7,
            popup=f"""
            <b>{row.Area}</b><br>
            Status: {row.Status}<br>
            Working Lights: {row.Working_Lights}/{row.Total_Lights}
            """
        ).add_to(m)
    
    # Add user location if available
    if st.session_state.user_location:
        folium.Marker(
            location=st.session_state.user_location,
            popup="Your Current Location",
            icon=folium.Icon(color="blue", icon="user", prefix="fa"),
            draggable=False
        ).add_to(m)
    
    # Display the map with forced refresh
    st_folium(m, width=725, key=f"map_{st.session_state.get('map_key', 0)}")
    
    # Show proximity alerts
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

# JavaScript message handler
components.html("""
<script>
window.addEventListener('message', function(event) {
    if (event.data.type === 'currentLocation') {
        window.parent.postMessage({
            isStreamlitMessage: true,
            type: 'setComponentValue',
            componentValue: event.data
        }, '*');
    }
});
</script>
""", height=0)