# planning_agent/agent.py

import os
import googlemaps
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
gmaps = googlemaps.Client(key=API_KEY)

def get_directions(origin, destination, waypoints=None):
    """
    Get optimized directions between origin and destination with optional waypoints.
    """
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
    places_result = gmaps.places_nearby(
        location=location,
        radius=radius,
        type=place_type
    )
    return places_result

if __name__ == "__main__":
    origin = "12.9716,77.5946"       # Example: Bangalore
    destination = "12.9352,77.6245"  # Example: Koramangala
    waypoints = ["12.9611,77.6387"]  # Example: MG Road

    result = get_directions(origin, destination, waypoints)
    print(result)

    cafes = get_places("12.9716,77.5946", 1500, "cafe")
    for place in cafes['results'][:3]:
        print(place["name"], place.get("rating"))

