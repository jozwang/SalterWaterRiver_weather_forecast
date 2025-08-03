# app.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta
import database

st.set_page_config(page_title="BoM Weather Comparison", layout="wide")

st.title("🌦️ BoM Weather: Forecast vs. Observation")
st.markdown("A simple app to compare forecasted maximum temperatures with actual observations.")

# --- Sidebar for Filters ---
st.sidebar.header("Filters")

# Get available locations from the database
try:
    available_locations = database.get_available_locations()
    # Ensure Dunalley is an option even if no forecast exists yet
    dunalley = "Dunalley (Henry anson)"
    if not available_locations:
        available_locations = [dunalley]
    elif dunalley not in available_locations:
        available_locations.append(dunalley)
        
    selected_location = st.sidebar.selectbox(
        "Select a Location",
        options=sorted(available_locations)
    )
except Exception as e:
    st.sidebar.error(f"Could not load locations: {e}")
    selected_location = "Dunalley (Henry anson)" # Default fallback

selected_date = st.sidebar.date_input(
    "Select a Date",
    value=date.today(),
    min_value=date.today() - timedelta(days=14),
    max_value=date.today() + timedelta(days=7) # Can look at future forecasts
)

# --- Main Page Content ---
if selected_location and selected_date:
    st.header(f"Comparison for {selected_location}")
    st.subheader(f"Date: {selected_date.strftime('%A, %d %B %Y')}")

    date_str = selected_date.isoformat()
    forecast, observations = database.get_comparison_data(selected_location, date_str)

    col1, col2 = st.columns(2)

    # Display Forecast
    with col1:
        st.subheader("🌡️ Forecast")
        if forecast and forecast['max_temp'] is not None:
            st.metric(label="Forecasted Max Temperature", value=f"{forecast['max_temp']} °C")
        else:
            st.warning("No forecast data available for this location and date.")

    # Display Observations
    with col2:
        st.subheader("📊 Observations")
        if observations:
            obs_df = pd.DataFrame(observations)
            # Convert datetime string to datetime objects for sorting and formatting
            obs_df['observation_datetime'] = pd.to_datetime(obs_df['observation_datetime'])
            
            # Find the max observed temperature for the day
            max_observed_temp = obs_df['air_temp'].max()
            st.metric(label="Highest Observed Temperature", value=f"{max_observed_temp:.1f} °C")
            
            st.write("---")
            st.write("Full Day Observations:")
            
            # Format for display
            display_df = obs_df.copy()
            display_df['Time'] = display_df['observation_datetime'].dt.strftime('%H:%M')
            display_df = display_df.rename(columns={'air_temp': 'Air Temp (°C)'})
            st.dataframe(display_df[['Time', 'Air Temp (°C)']], use_container_width=True, hide_index=True)

        else:
            st.warning("No observation data available for this location and date.")

else:
    st.info("Please select a location and date from the sidebar to see the comparison.")