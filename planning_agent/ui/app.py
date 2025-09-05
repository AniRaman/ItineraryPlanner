import streamlit as st
import folium
from streamlit_folium import st_folium
import sys
import os
import asyncio
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types

# Import all agent functions
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'agent'))
from agent import (
    get_directions, get_place_autocomplete, get_place_details, 
    get_places_nearby, get_places_text_search, cached_place_details, 
    cached_nearby_search, sample_route_points, get_pois_along_route,
    search_pois_along_route, validate_itinerary,
    root_agent
)

# Setup Session Service and Runner
session_service = InMemorySessionService()

# Define constants for identifying the interaction context  
APP_NAME = "itinerary_planner_app"
USER_ID = "user_1" 
SESSION_ID = "session_001"

# Create the session
session = asyncio.run(session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=SESSION_ID
))
print(f"Session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")

# Create the runner
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service
)

# Removed rigid mappings - Agent will intelligently handle POI discovery and categorization

async def generate_itinerary_async(route_points, num_days, preference, budget_level, origin_name, destination_name, origin_lat, origin_lng):
    """Generate intelligent itinerary using ADK Agent with async session management"""
    
    # Build the query string for the agent
    query = f"""Create a {num_days}-day itinerary from {origin_name} to {destination_name}.

Route Information:
- Route points: {route_points}
- Origin coordinates: {origin_lat}, {origin_lng}

User Preferences:
- Days: {num_days}
- Budget: {budget_level}
- Preference: {preference}
"""

    print(f"\n>>> User Query: {query}")
    
    # Prepare the user's message in ADK format
    content = types.Content(role='user', parts=[types.Part(text=query)])
    
    final_response_text = "Agent did not produce a final response."  # Default
    debug_events = []  # Store debug information
    
    try:
        # Run the agent and process events
        async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=content):
            # Debug: Store event information
            debug_info = f"[Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}"
            debug_events.append(debug_info)
            print("DEBUG: debugInfo ", debug_info)
            
            # Check for final response
            if event.is_final_response():
                if event.content and event.content.parts:
                    # Get text response from the first part
                    final_response_text = event.content.parts[0].text
                elif event.actions and event.actions.escalate:
                    # Handle escalations
                    final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
                break  # Stop processing events once final response is found
                
        print(f"<<< Agent Response: {final_response_text}")
        
        return {
            "itinerary": final_response_text,
            "debug_events": debug_events
        }
        
    except Exception as e:
        error_msg = f"Error generating itinerary: {str(e)}"
        print(error_msg)
        return {
            "itinerary": error_msg,
            "debug_events": debug_events
        }

st.title("🗺️ Itinerary Route Planner")

# User input section for itinerary preferences
with st.sidebar:
    st.header("🎯 Trip Preferences")
    
    num_days = st.selectbox("📅 Number of Days", [1, 2, 3, 4, 5], index=1)
    
    budget_level = st.selectbox("💰 Budget", 
        ["budget", "mid-range", "luxury"], 
        index=1
    )
    
    preference = st.selectbox("🎨 Preference", [
        "family-friendly", "nightlife", "beach", "mountains", 
        "historical", "food", "shopping", "nature"
    ])
    
    generate_itinerary = st.button("🗓️ Generate Itinerary", type="primary")

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
            
            # Generate Itinerary Section
            if generate_itinerary:
                st.markdown("---")
                st.subheader("🤖 Intelligent Agent Creating Your Itinerary...")
                
                # DEBUG: Show input to agent
                with st.expander("🔍 DEBUG: Agent Input", expanded=False):
                    st.write("**Input sent to Intelligent Agent:**")
                    route_points = sample_route_points(directions)
                    agent_input = {
                        "origin": origin_data["name"],
                        "destination": dest_data["name"], 
                        "origin_coordinates": [origin_data["lat"], origin_data["lng"]],
                        "route_points": route_points[:5],  # Show first 5 points
                        "total_route_points": len(route_points),
                        "days": num_days,
                        "budget": budget_level,
                        "preference": preference
                    }
                    st.json(agent_input)
                
                with st.spinner("Agent is intelligently discovering POIs and creating your itinerary..."):
                    try:
                        # Generate route points for agent
                        route_points = sample_route_points(directions)
                        
                        # Convert route points to format agent expects
                        route_points_for_agent = [{"lat": lat, "lng": lng} for lat, lng in route_points]
                        
                        # Call intelligent agent using asyncio
                        result = asyncio.run(generate_itinerary_async(
                            route_points_for_agent,
                            num_days, 
                            preference, 
                            budget_level,
                            origin_data["name"], 
                            dest_data["name"],
                            origin_data["lat"], 
                            origin_data["lng"]
                        ))
                        
                        itinerary = result["itinerary"]
                        debug_events = result["debug_events"]
                        
                        # DEBUG: Show agent output and events
                        with st.expander("🔍 DEBUG: Agent Output & Events", expanded=False):
                            st.write("**Debug Events:**")
                            for event in debug_events:
                                st.text(event)
                            st.write("**Raw Agent Response:**")
                            st.text(itinerary[:500] + "..." if len(itinerary) > 500 else itinerary)
                        
                        # Display the final itinerary
                        st.success("✅ Your Intelligent Itinerary is Ready!")
                        st.markdown(itinerary)
                        
                        # Show summary
                        st.subheader("🤖 AI Agent Summary")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Days Planned", num_days)
                        with col2:
                            st.metric("Budget Level", budget_level.title())
                        with col3:
                            st.metric("Preference", preference.title().replace('-', ' '))
                        
                    except Exception as e:
                        st.error(f"Error generating itinerary: {e}")
                        st.exception(e)
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
