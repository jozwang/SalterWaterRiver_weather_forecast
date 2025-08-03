# app.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta
import database
import fetch_data # We now import the fetch_data script

def perform_first_time_setup():
    """
    Creates the database and populates it with initial data.
    This function runs only if the database is empty.
    """
    with st.spinner("Performing first-time data setup... This might take a minute."):
        st.info("Creating database tables...")
        database.init_db()

        # 1. Fetch and store forecasts
        st.info("Fetching forecast data from BoM FTP...")
        forecast_content = fetch_data.fetch_forecasts()
        if forecast_content:
            parsed_forecasts = fetch_data.parse_forecasts(forecast_content)
            database.upsert_forecasts(parsed_forecasts)
            st.info(f"Successfully stored {len(parsed_forecasts)} forecast records.")
        else:
            st.error("Failed to fetch forecast data. The app may not have all locations available.")

        # 2. Fetch and store observations
        st.info("Fetching observation data for Dunalley...")
        parsed_observations = fetch_data.fetch_observations()
        if parsed_observations:
            database.insert_observations(parsed_observations)
            st.info(f"Successfully stored {len(parsed_observations)} observation records.")
        else:
            st.warning("Failed to fetch observation data.")

    st.success("First-time setup complete! Loading the app...")
    st.rerun()

# --- Main App Logic ---

# Check if the database exists and has data. If not, run the setup.
# We need to make sure the tables exist before we can query them.
database.init_db() 
try:
    if not database.get_available_locations():
        perform_first_time_setup()
except Exception:
    # This might happen if the table doesn't exist yet, so we run setup.
    perform_first_time_setup()


# --- Page Configuration and UI ---
st.set_page_config(page_title="BoM Weather Comparison", layout="wide")

st.title("🌦️ BoM Weather: Forecast vs. Observation")
st.markdown("A simple app to compare forecasted maximum temperatures with actual observations.")

# --- Sidebar for Filters ---
st.sidebar.header("Filters")

try:
    available_locations = database.get_available_locations()
    if not available_locations:
        st.sidebar.warning("No locations found. Data might still be loading.")
        st.stop() # Stop the script if there are no locations to show

    selected_location = st.sidebar.selectbox(
        "Select a Location",
        options=sorted(available_locations)
    )
except Exception as e:
    st.error(f"A database error occurred: {e}")
    st.info("The app might be performing its first-time setup. Please wait a moment and refresh.")
    st.stop()


selected_date = st.sidebar.date_input(
    "Select a Date",
    value=date.today(),
    min_value=date.today() - timedelta(days=14),
    max_value=date.today() + timedelta(days=7)
)

# --- Main Page Content ---
if selected_location and selected_date:
    st.header(f"Comparison for {selected_location}")
    st.subheader(f"Date: {selected_date.strftime('%A, %d %B %Y')}")

    date_str = selected_date.isoformat()
    forecast, observations = database.get_comparison_data(selected_location, date_str)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🌡️ Forecast")
        if forecast and forecast['max_temp'] is not None:
            st.metric(label="Forecasted Max Temperature", value=f"{forecast['max_temp']} °C")
        else:
            st.warning("No forecast data available for this location and date.")

    with col2:
        st.subheader("📊 Observations")
        if observations:
            obs_df = pd.DataFrame(observations)
            obs_df['observation_datetime'] = pd.to_datetime(obs_df['observation_datetime'])
            max_observed_temp = obs_df['air_temp'].max()
            st.metric(label="Highest Observed Temperature", value=f"{max_observed_temp:.1f} °C")
            
            st.write("---")
            st.write("Full Day Observations:")
            
            display_df = obs_df.copy()
            display_df['Time'] = display_df['observation_datetime'].dt.strftime('%H:%M')
            display_df = display_df.rename(columns={'air_temp': 'Air Temp (°C)'})
            st.dataframe(display_df[['Time', 'Air Temp (°C)']], use_container_width=True, hide_index=True)
        else:
            st.warning("No observation data available for this location and date.")
