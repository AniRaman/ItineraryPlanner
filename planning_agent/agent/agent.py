# planning_agent/agent.py

import os
import googlemaps
import requests
import json
from dotenv import load_dotenv
from functools import lru_cache
import google.generativeai as genai
import re
import asyncio
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types


# Load environment variables
load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Initialize clients only if API keys are available
gmaps = None
if GOOGLE_MAPS_API_KEY:
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    genai.configure(api_key=GOOGLE_API_KEY)

def get_directions(origin, destination, waypoints=None):
    """
    Get optimized directions between origin and destination with optional waypoints.
    """
    if not gmaps:
        raise ValueError("Google Maps client not initialized. Please set GOOGLE_API_KEY environment variable.")
    
    directions_result = gmaps.directions(
        origin,
        destination,
        waypoints=waypoints,
        optimize_waypoints=True,
        mode="driving"
    )
    return directions_result

def get_places(location, radius=1000, place_type="cafe"):
    """
    Get nearby places (like cafes, restaurants) around a location.
    """
    if not gmaps:
        raise ValueError("Google Maps client not initialized. Please set GOOGLE_API_KEY environment variable.")
    
    places_result = gmaps.places_nearby(
        location=location,
        radius=radius,
        type=place_type
    )
    return places_result

# Additional API functions moved from UI layer
@lru_cache(maxsize=500)
def cached_place_details(place_id):
    return get_place_details(place_id)

@lru_cache(maxsize=200)  
def cached_nearby_search(lat, lng, poi_type, radius=1000):
    return get_places_nearby(lat, lng, poi_type, radius)

def get_place_details(place_id):
    url = f"https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id, 
        "key": GOOGLE_MAPS_API_KEY,
        "fields": "geometry,name,rating,price_level,opening_hours,photos,types,formatted_address"
    }
    res = requests.get(url, params=params).json()
    return res.get("result", {})

def get_places_nearby(lat, lng, poi_type, radius=1000):
    """Get nearby places of specific type"""
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": f"{lat},{lng}",
        "radius": radius,
        "type": poi_type,
        "key": GOOGLE_MAPS_API_KEY
    }
    res = requests.get(url, params=params).json()
    return res.get("results", [])

def get_places_text_search(query, lat, lng, radius=5000):
    """Fallback text search for POIs"""
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": query,
        "location": f"{lat},{lng}",
        "radius": radius,
        "key": GOOGLE_MAPS_API_KEY
    }
    res = requests.get(url, params=params).json()
    return res.get("results", [])

def get_place_autocomplete(query):
    url = f"https://maps.googleapis.com/maps/api/place/autocomplete/json"
    params = {
        "input": query,
        "key": GOOGLE_MAPS_API_KEY,
        "types": "geocode"
    }
    res = requests.get(url, params=params).json()
    return res.get("predictions", [])

def sample_route_points(directions_result, interval_meters=500):
    """Sample points along route polyline every interval_meters"""
    if not directions_result:
        return []
    
    route = directions_result[0]
    points = []
    
    for leg in route['legs']:
        for step in leg['steps']:
            # Add step start location
            start = step['start_location']
            points.append((start['lat'], start['lng']))
            
            # TODO: Add intermediate points along step polyline based on interval
            # For now, just using step endpoints
    
    # Add final destination
    final_leg = route['legs'][-1]
    end = final_leg['end_location'] 
    points.append((end['lat'], end['lng']))
    
    return points

def get_pois_along_route(route_points, search_terms, threshold=5):
    """Get POIs along route points using flexible search terms
    
    Args:
        route_points: List of (lat, lng) tuples along the route
        search_terms: List of search terms (e.g., ["bar", "restaurant", "museum"])
        threshold: Min results from nearby search before falling back to text search
    """
    all_pois = []
    
    for lat, lng in route_points:
        for search_term in search_terms:
            try:
                # First try nearby search with the search term as POI type
                pois = cached_nearby_search(lat, lng, search_term)
                
                if len(pois) < threshold:
                    # Simple fallback - use agent's term directly in text search
                    try:
                        search_results = get_places_text_search(f"{search_term} near {lat},{lng}", lat, lng)
                        pois.extend(search_results)
                    except:
                        continue
                
                all_pois.extend(pois)
            except Exception as e:
                print(f"Error fetching POIs for {search_term}: {e}")
                continue
    
    # Deduplicate by place_id
    unique_pois = {poi.get('place_id'): poi for poi in all_pois if poi.get('place_id')}
    return list(unique_pois.values())

# Agent Tools
def search_pois_along_route(route_points: list[dict], preference: str, budget_level: str, origin_lat: float, origin_lng: float) -> dict:
    """Retrieves the POIs along the route based on the user's preferences and budget level.

    Returns:
        dict: A dictionary containing the POIs or an error message.
    """
    try:
        print("DEBUG: search_pois_along_route with filtering")
        
        # Hardcoded preference to search terms mapping
        preference_mapping = {
            "nightlife": ["bar", "night_club", "restaurant", "movie_theater", "entertainment"],
            "family-friendly": ["amusement_park", "zoo", "aquarium", "park", "restaurant"],
            "food": ["restaurant", "cafe", "bakery", "meal_takeaway"],
            "nature": ["park", "hiking_area", "natural_feature", "campground"],
            "historical": ["museum", "tourist_attraction", "historical_site", "art_gallery"],
            "shopping": ["shopping_mall", "store", "clothing_store", "department_store"],
            "beach": ["beach", "water_sports", "resort", "seafood_restaurant"],
            "mountains": ["hiking_area", "scenic_lookout", "mountain", "ski_resort"]
        }
        
        search_terms = preference_mapping.get(preference.lower(), ["tourist_attraction", "restaurant"])
        print(f"DEBUG: Using search terms for {preference}: {search_terms}")
        
        # Convert route points to tuples
        route_tuples = [(point["lat"], point["lng"]) for point in route_points]
        
        # Get ALL POIs using the flexible function (no limit initially)
        all_pois = get_pois_along_route(route_tuples, search_terms)
        print(f"DEBUG: Found {len(all_pois)} total POIs")
        
        # Budget filtering
        budget_mapping = {
            "budget": [0, 1],
            "mid-range": [1, 2, 3], 
            "luxury": [3, 4]
        }
        allowed_prices = budget_mapping.get(budget_level, [0, 1, 2, 3, 4])
        
        # Group POIs by search term category first
        category_pois = {}
        for search_term in search_terms:
            category_pois[search_term] = []
        
        # Categorize and filter POIs
        for poi in all_pois:
            # Check budget first
            price_level = poi.get('price_level')
            if price_level is not None and price_level not in allowed_prices:
                continue  # Skip if doesn't fit budget
                
            # Categorize by POI types (from the 'types' field)
            poi_types = poi.get('types', [])
            assigned = False
            
            for search_term in search_terms:
                # Check if search_term matches any of the POI's types
                if search_term in poi_types:
                    category_pois[search_term].append(poi)
                    assigned = True
                    break  # Only add to first matching category
            
            # If not assigned to any specific category, try to find best match
            if not assigned:
                for search_term in search_terms:
                    # More flexible matching for compound terms
                    if any(search_term in poi_type or poi_type in search_term for poi_type in poi_types):
                        category_pois[search_term].append(poi)
                        break
        
        print(f"DEBUG: POIs per category: {[(cat, len(pois)) for cat, pois in category_pois.items()]}")
        
        # Score and get top 5 from each category
        final_pois = []
        for search_term, pois in category_pois.items():
            if not pois:
                print(f"DEBUG: No POIs found for category: {search_term}")
                continue
                
            # Score POIs in this category
            scored_category_pois = []
            for poi in pois:
                score = 0
                
                # Rating score
                rating = poi.get('rating', 3.0)
                score += rating * 20  # Max 100 points
                
                # Distance penalty (closer to origin is better)
                poi_lat = poi.get('geometry', {}).get('location', {}).get('lat')
                poi_lng = poi.get('geometry', {}).get('location', {}).get('lng')
                if poi_lat and poi_lng:
                    distance = ((poi_lat - origin_lat) ** 2 + (poi_lng - origin_lng) ** 2) ** 0.5
                    distance_penalty = min(distance * 10, 30)
                    score -= distance_penalty
                
                scored_category_pois.append((max(score, 0), poi))
            
            # Sort by score and get top 5 from this category
            scored_category_pois.sort(reverse=True, key=lambda x: x[0])
            top_5_category = [poi for score, poi in scored_category_pois[:5]]
            final_pois.extend(top_5_category)
            print(f"DEBUG: Added top {len(top_5_category)} POIs from category: {search_term}")
        
        print(f"DEBUG: Returning {len(final_pois)} categorized POIs")
        print("DEBUG: final_pois", final_pois)
        return {"pois": final_pois}
    except Exception as e:
        return {"error": f"Error searching POIs: {str(e)}"}

def validate_itinerary(itinerary_text: str, original_pois: list[dict]) -> dict:
    """Validates the itinerary.

    Returns:
        dict: A dictionary containing the itinerary validation information.
    """
    try:
        original_names = [poi.get('name', '').lower() for poi in original_pois if poi.get('name')]
        
        # Count how many original POIs are mentioned in the output
        mentioned_count = 0
        for name in original_names:
            if name in itinerary_text.lower():
                mentioned_count += 1
        
        coverage_percentage = (mentioned_count / len(original_names) * 100) if original_names else 0
        
        validation_result = {
            "coverage_percentage": round(coverage_percentage, 1),
            "mentioned_count": mentioned_count,
            "total_pois": len(original_names),
            "is_valid": coverage_percentage >= 50  # At least 50% of POIs should be mentioned
        }
        return validation_result
    except Exception as e:
        return {"error": f"Error validating itinerary: {str(e)}"}

# Import required classes for new agent structure
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool

def create_itinerary_agent() -> LlmAgent:
    """Agent for creating personalized travel itineraries."""
    return LlmAgent(
        model="gemini-2.0-flash",
        name="itinerary_planner",
        description="Intelligent travel planner that discovers POIs and creates itineraries.",
        instruction="""            
            1. Call search_pois_along_route to discover POIs based on user interests. With that POIs generate Itinerary. Then validate that itinerary with validate_itinerary function.
            2. Now you should generate itinerary with the POIs(dict) received from step 1. No functions for this you should do one your own.
            3. Call validate_itinerary with your written itinerary text and the original POIs.
            Make sure to group nearby places together to minimize travel time and include logical meal breaks throughout each day.
        """,
        tools=[
            FunctionTool(func=search_pois_along_route),
            FunctionTool(func=validate_itinerary),
        ],
    )


root_agent = create_itinerary_agent()

# Set up session and runner
session_service_gemini = InMemorySessionService()
# Note: Session will be created async when needed

runner_gemini = Runner(
    agent=root_agent,
    app_name="itinerary_planner_app",
    session_service=session_service_gemini
)

async def call_agent_async(query: str, runner, user_id, session_id):
    """Sends a query to the agent and prints the final response."""
    print(f"\n>>> User Query: {query}")

    # Prepare the user's message in ADK format
    content = types.Content(role='user', parts=[types.Part(text=query)])
    
    final_response_text = "Agent did not produce a final response."
    
    # Execute the agent and find the final response
    async for event in runner.run_async(
        user_id=user_id, 
        session_id=session_id, 
        new_message=content
    ):
        print(f"DEBUG: Event - Author: {event.author}, Final: {event.is_final_response()}")
        print("DEBUG: Event - Content: ", event.content)
        if event.is_final_response():
            if event.content and event.content.parts:
                # Handle text parts only
                text_parts = [part.text for part in event.content.parts if hasattr(part, 'text') and part.text]
                if text_parts:
                    final_response_text = " ".join(text_parts)
                else:
                    final_response_text = "Agent completed but returned no text response."
            break
            
    print(f"<<< Agent Response: {final_response_text}")
    return final_response_text


# Test the Gemini agent
async def test_gemini_agent():
    print("\n--- Testing Gemini Agent ---")
    # Create session first
    await session_service_gemini.create_session(
        app_name="itinerary_planner_app",
        user_id="user_1", 
        session_id="session_gemini"
    )
    
    await call_agent_async(
        '''Create a 1-day itinerary from Whitefield, Bengaluru, Karnataka, India to Yelahanka, Bengaluru, Karnataka, India.

Route Information:
- Route points: [{'lat': 12.9698235, 'lng': 77.7499503}, {'lat': 12.9830082, 'lng': 77.7522048}, {'lat': 12.987888, 'lng': 77.7334051}, {'lat': 12.9842764, 'lng': 77.7290893}, {'lat': 12.9865946, 'lng': 77.7317473}, {'lat': 12.9881541, 'lng': 77.731731}, {'lat': 12.9917587, 'lng': 77.7155816}, {'lat': 12.9910054, 'lng': 77.7147251}, {'lat': 12.9903995, 'lng': 77.7140484}, {'lat': 13.0002981, 'lng': 77.68074849999999}, {'lat': 13.0419689, 'lng': 77.5938994}, {'lat': 13.0426893, 'lng': 77.590401}, {'lat': 13.0949516, 'lng': 77.5975587}, {'lat': 13.0950005, 'lng': 77.59742589999999}, {'lat': 13.1154543, 'lng': 77.6070896}, {'lat': 13.1154897, 'lng': 77.60700849999999}]
- Origin coordinates: 12.9698196, 77.7499721

User Preferences:
- Days: 1
- Budget: mid-range
- Preference: nightlife
''',
        runner=runner_gemini,
        user_id="user_1",
        session_id="session_gemini"
    )

if __name__ == "__main__":
    asyncio.run(test_gemini_agent())