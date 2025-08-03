# fetch_data.py
import ftplib
import logging
import re
import requests
import io
import pandas as pd
from datetime import datetime, timedelta
import database

# --- Configuration ---
FTP_URL = "ftp.bom.gov.au"
FORECAST_PATH = "/anon/gen/fwo/"
FORECAST_FILE = "IDT16710.txt"
OBSERVATION_URL = "http://www.bom.gov.au/fwo/IDT60801/IDT60801.94951.json"
OBSERVATION_LOCATION = "Dunalley (Henry anson)"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_forecasts():
    """Connects to the BoM FTP and retrieves the Tasmanian forecast file."""
    logging.info(f"Connecting to FTP server: {FTP_URL}")
    try:
        with ftplib.FTP(FTP_URL) as ftp:
            ftp.login()
            ftp.cwd(FORECAST_PATH)
            
            # Use a BytesIO object to "hold" the file in memory
            file_buffer = io.BytesIO()
            ftp.retrbinary(f"RETR {FORECAST_FILE}", file_buffer.write)
            
            # Decode the bytes to a string
            file_buffer.seek(0)
            file_content = file_buffer.read().decode("utf-8")
            
            logging.info(f"Successfully downloaded {FORECAST_FILE}")
            return file_content
    except Exception as e:
        logging.error(f"Failed to fetch forecast from FTP: {e}")
        return None

def parse_forecasts(file_content):
    """Parses the raw text of the forecast file to extract max temps."""
    if not file_content:
        return []
    
    # Regex to find a location line and its associated max temperature
    # Looks for a line starting with a capitalised word (the location)
    # followed by anything, then "Maximum" and a number.
    pattern = re.compile(r"^(?P<location>[A-Z][\w\s\(\)-]+?)\s+.*?Maximum\s+(?P<max_temp>\d+)\.", re.MULTILINE)
    
    # Extract issue date to calculate forecast date
    issue_date_match = re.search(r"Issued at .*? on (\w+ \d{1,2} \w+ \d{4})", file_content)
    if not issue_date_match:
        logging.error("Could not find issue date in forecast file.")
        return []
    
    try:
        # BoM uses a non-standard month abbreviation, so we correct it
        date_str = issue_date_match.group(1).replace("Sept", "September")
        base_date = datetime.strptime(date_str, "%A %d %B %Y").date()
    except ValueError as e:
        logging.error(f"Could not parse issue date: {e}")
        return []

    forecasts = []
    # Split the file by days (e.g., "for Saturday.", "for Sunday.")
    day_sections = re.split(r"Forecast for the rest of|Forecast for", file_content)[1:]

    for i, section in enumerate(day_sections):
        forecast_date = base_date + timedelta(days=i)
        matches = pattern.finditer(section)
        for match in matches:
            data = match.groupdict()
            forecasts.append({
                "location": data["location"].strip(),
                "forecast_date": forecast_date.isoformat(),
                "max_temp": int(data["max_temp"])
            })
            
    logging.info(f"Parsed {len(forecasts)} forecasts.")
    return forecasts

def fetch_observations():
    """Fetches and parses the observation JSON from the BoM website."""
    logging.info(f"Fetching observations from {OBSERVATION_URL}")
    try:
        response = requests.get(OBSERVATION_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        obs_list = data.get("observations", {}).get("data", [])
        if not obs_list:
            logging.warning("No observation data found in JSON response.")
            return []
            
        parsed_obs = []
        for obs in obs_list:
            # Check if air_temp exists and is not None
            if obs.get('air_temp') is not None:
                parsed_obs.append({
                    "location": OBSERVATION_LOCATION,
                    "observation_datetime": f"{obs['local_date_time_full']}{obs['aifstime_utc']}",
                    "air_temp": float(obs['air_temp'])
                })

        logging.info(f"Fetched and parsed {len(parsed_obs)} observation records.")
        return parsed_obs

    except requests.RequestException as e:
        logging.error(f"Failed to fetch observations: {e}")
        return []

if __name__ == "__main__":
    # --- Main Execution ---
    database.init_db()
    
    # Process Forecasts
    forecast_content = fetch_forecasts()
    if forecast_content:
        parsed_forecasts_data = parse_forecasts(forecast_content)
        database.upsert_forecasts(parsed_forecasts_data)

    # Process Observations
    parsed_observations_data = fetch_observations()
    if parsed_observations_data:
        database.insert_observations(parsed_observations_data)

    # Clean up old records
    database.cleanup_old_data()
    
    logging.info("Data fetch and update process complete.")