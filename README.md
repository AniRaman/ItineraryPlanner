# 🗺️ Itinerary Planning Agent

An intelligent travel itinerary planner powered by Google ADK (Agent Development Kit) and Google Maps API. The system discovers Points of Interest (POIs) along your route and creates personalized itineraries based on your preferences and budget.

## 🌟 Features

- **Smart POI Discovery**: Finds relevant places along your travel route
- **Preference-Based Planning**: Tailors suggestions to your interests (nightlife, family-friendly, food, nature, etc.)
- **Budget-Aware**: Filters options based on your budget level (budget, mid-range, luxury)
- **Accuracy Validation**: Prevents AI hallucination by validating against real search results
- **Clean Data Filtering**: Removes closed businesses and unnecessary fields
- **Interactive UI**: Web interface for easy trip planning

## 🛠️ Prerequisites

- Python 3.11+
- Google Maps API key
- Google AI API key (Gemini)

## 🚀 Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Itinerary
   ```

2. **Install dependencies**
   ```bash
   pip install googlemaps requests python-dotenv google-generativeai streamlit folium streamlit-folium
   pip install google-adk  # Google Agent Development Kit
   ```

3. **Set up environment variables**
   Create a `.env` file in the project root:
   ```env
   GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
   GOOGLE_API_KEY=your_google_ai_api_key_here
   ```

   **Getting API Keys:**
   - **Google Maps API**: Go to [Google Cloud Console](https://console.cloud.google.com/), enable Maps API, and create credentials
   - **Google AI API**: Visit [Google AI Studio](https://aistudio.google.com/) to get your Gemini API key

## 🎯 Usage

### Option 1: Agent Only (Command Line)

Run the agent directly for testing and development:

```bash
cd planning_agent/agent
python agent.py
```

This will:
- Run a test query from Whitefield to Yelahanka, Bengaluru
- Show debug output of POI discovery and filtering
- Generate a sample nightlife itinerary
- Display validation results

### Option 2: Web Interface (Streamlit)

Launch the interactive web application:

```bash
cd planning_agent/ui
streamlit run app.py
```

Then open your browser to `http://localhost:8501`

**Using the Web Interface:**
1. **Set Preferences**: Choose trip duration, budget, and interests in the sidebar
2. **Enter Locations**: Type origin and destination in the input fields
3. **Select from Suggestions**: Choose from Google's autocomplete suggestions
4. **View Route**: See your route plotted on the interactive map
5. **Generate Itinerary**: Click "Generate Itinerary" to create your personalized plan

## 🏗️ Project Structure

```
Itinerary/
├── planning_agent/
│   ├── agent/
│   │   ├── agent.py          # Core agent logic and POI functions
│   │   └── __init__.py       # Package initialization
│   └── ui/
│       └── app.py            # Streamlit web interface
└── README.md                 # This file
```

## 🤖 How It Works

### 1. POI Discovery
- Samples points along your route
- Searches for relevant places using Google Places API
- Applies preference-based filtering (nightlife → bars, clubs, restaurants)
- Removes closed/temporary businesses

### 2. Smart Filtering
The system filters POI data to include only essential information:
- **Location & Identity**: Name, place_id, coordinates, address
- **Quality Indicators**: Rating, review count, business status  
- **Operational Info**: Opening hours, price level, place types

### 3. Itinerary Generation
- Uses Google's Gemini AI to create narrative-style itineraries
- Groups nearby places to minimize travel time
- Respects logical activity flow (e.g., dinner → bar → nightclub)
- Avoids time slots for natural storytelling

### 4. Validation
- Checks that generated itineraries use real POIs from search results
- Prevents AI hallucination of fake places
- Focuses on accuracy over arbitrary coverage percentages

## 🎨 Supported Preferences

- **Nightlife**: Bars, nightclubs, restaurants, entertainment venues
- **Family-friendly**: Parks, zoos, family restaurants, attractions
- **Food**: Restaurants, cafes, bakeries, food markets
- **Nature**: Parks, hiking areas, natural features
- **Historical**: Museums, monuments, cultural sites
- **Shopping**: Malls, stores, markets
- **Beach**: Coastal activities, water sports, seafood
- **Mountains**: Hiking, scenic viewpoints, mountain resorts

## 🔧 Configuration

### Budget Levels
- **Budget**: Price level 0-1
- **Mid-range**: Price level 1-3
- **Luxury**: Price level 3-4

### Customization
To modify search preferences or add new categories, edit the `preference_mapping` dictionary in `agent.py` (lines 180-189).

## 🐛 Troubleshooting

### Common Issues

**"Google Maps client not initialized"**
- Verify your `GOOGLE_MAPS_API_KEY` in the `.env` file
- Ensure the Maps API is enabled in Google Cloud Console

**"No POIs found"**
- Check your internet connection
- Verify API quotas aren't exceeded
- Try a different location or expand the search radius

**Unicode/Character Encoding Errors**
- The system automatically handles emoji and special characters in place names
- If issues persist, check the filtering logic in `search_pois_along_route`

### Debug Mode
When running the agent directly (`python agent.py`), debug output shows:
- Number of POIs found and filtered
- Category distribution
- Scoring and selection process

## 📝 License

This project is open source. Please ensure you comply with Google's API terms of service when using their services.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Verify your API keys and quotas
3. Review the debug output when running in agent mode
4. Create an issue with detailed error messages and steps to reproduce