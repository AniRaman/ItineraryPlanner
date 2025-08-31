import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
import sys
import os

# Import get_directions from agent
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agent'))
from agent import get_directions

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def get_place_autocomplete(query):
    url = f"https://maps.googleapis.com/maps/api/place/autocomplete/json"
    params = {
        "input": query,
        "key": GOOGLE_API_KEY,
        "types": "geocode"
    }
    res = requests.get(url, params=params).json()
    return res.get("predictions", [])

def get_place_details(place_id):
    url = f"https://maps.googleapis.com/maps/api/place/details/json"
    params = {"place_id": place_id, "key": GOOGLE_API_KEY}
    res = requests.get(url, params=params).json()
    return res.get("result", {})

st.title("🗺️ Itinerary Route Planner")

# Create two columns for origin and destination
col1, col2 = st.columns(2)

# Origin selection
with col1:
    st.subheader("🚩 Origin")
    origin_query = st.text_input("Start typing origin...", key="origin_input")
    origin_data = None
    
    if origin_query and len(origin_query) > 2:
        origin_suggestions = get_place_autocomplete(origin_query)
        if origin_suggestions:
            origin_choice = st.selectbox(
                "Origin Suggestions:",
                [s["description"] for s in origin_suggestions],
                key="origin_selectbox"
            )
            
            if origin_choice:
                selected = next(s for s in origin_suggestions if s["description"] == origin_choice)
                details = get_place_details(selected["place_id"])
                lat = details["geometry"]["location"]["lat"]
                lng = details["geometry"]["location"]["lng"]
                
                st.success(f"📍 {origin_choice}")
                origin_data = {
                    "name": origin_choice,
                    "lat": lat,
                    "lng": lng,
                    "coordinates": f"{lat},{lng}"
                }

# Destination selection  
with col2:
    st.subheader("🏁 Destination")
    dest_query = st.text_input("Start typing destination...", key="dest_input")
    dest_data = None
    
    if dest_query and len(dest_query) > 2:
        dest_suggestions = get_place_autocomplete(dest_query)
        if dest_suggestions:
            dest_choice = st.selectbox(
                "Destination Suggestions:",
                [s["description"] for s in dest_suggestions],
                key="dest_selectbox"
            )
            
            if dest_choice:
                selected = next(s for s in dest_suggestions if s["description"] == dest_choice)
                details = get_place_details(selected["place_id"])
                lat = details["geometry"]["location"]["lat"]
                lng = details["geometry"]["location"]["lng"]
                
                st.success(f"📍 {dest_choice}")
                dest_data = {
                    "name": dest_choice,
                    "lat": lat,
                    "lng": lng,
                    "coordinates": f"{lat},{lng}"
                }

# Show map and route
st.subheader("🗺️ Map")

if origin_data and dest_data:
    # Get route using existing get_directions function
    try:
        directions = get_directions(origin_data["coordinates"], dest_data["coordinates"])
        
        if directions:
            # Create map centered between origin and destination
            center_lat = (origin_data["lat"] + dest_data["lat"]) / 2
            center_lng = (origin_data["lng"] + dest_data["lng"]) / 2
            m = folium.Map(location=[center_lat, center_lng], zoom_start=12)
            
            # Add origin marker
            folium.Marker(
                [origin_data["lat"], origin_data["lng"]], 
                tooltip=f"Origin: {origin_data['name']}",
                icon=folium.Icon(color='green', icon='play')
            ).add_to(m)
            
            # Add destination marker
            folium.Marker(
                [dest_data["lat"], dest_data["lng"]], 
                tooltip=f"Destination: {dest_data['name']}",
                icon=folium.Icon(color='red', icon='stop')
            ).add_to(m)
            
            # Draw route
            route = directions[0]
            legs = route['legs'][0]
            
            # Show route info
            st.info(f"**Distance:** {legs['distance']['text']} | **Duration:** {legs['duration']['text']}")
            
            # Extract route coordinates and draw line
            route_coords = []
            for step in legs['steps']:
                route_coords.append([step['start_location']['lat'], step['start_location']['lng']])
            route_coords.append([legs['end_location']['lat'], legs['end_location']['lng']])
            
            folium.PolyLine(route_coords, weight=5, color='blue', opacity=0.8).add_to(m)
            
            st_folium(m, width=700, height=500)
        else:
            st.error("Could not find route")
    except Exception as e:
        st.error(f"Error: {e}")
        
elif origin_data or dest_data:
    # Show single location
    location = origin_data or dest_data
    m = folium.Map(location=[location["lat"], location["lng"]], zoom_start=14)
    color = 'green' if origin_data else 'red' 
    icon = 'play' if origin_data else 'stop'
    folium.Marker([location["lat"], location["lng"]], tooltip=location['name'], 
                 icon=folium.Icon(color=color, icon=icon)).add_to(m)
    st_folium(m, width=700, height=500)
else:
    # Default map
    m = folium.Map(location=[40.7128, -74.0060], zoom_start=10)  # Default to NYC
    st_folium(m, width=700, height=500)
