# database.py
import sqlite3
import logging
from datetime import datetime

DB_FILE = "weather_data.db"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection():
    """Establishes a connection to the database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialises the database tables if they don't exist."""
    logging.info("Initialising database...")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Forecasts table with UPSERT capability on (location, forecast_date)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            forecast_date TEXT NOT NULL,
            max_temp INTEGER,
            last_updated_at TEXT NOT NULL,
            UNIQUE(location, forecast_date)
        )
        """)
        # Observations table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT NOT NULL,
            observation_datetime TEXT NOT NULL,
            air_temp REAL,
            last_updated_at TEXT NOT NULL
        )
        """)
        conn.commit()
    logging.info("Database initialised.")

def upsert_forecasts(forecast_data):
    """
    Inserts or updates forecast data.
    forecast_data should be a list of tuples: (location, forecast_date, max_temp)
    """
    if not forecast_data:
        logging.info("No forecast data to upsert.")
        return

    logging.info(f"Upserting {len(forecast_data)} forecast records.")
    now = datetime.utcnow().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Add the last_updated_at timestamp to each record
        data_to_insert = [
            (rec['location'], rec['forecast_date'], rec['max_temp'], now)
            for rec in forecast_data
        ]
        
        cursor.executemany("""
        INSERT INTO forecasts (location, forecast_date, max_temp, last_updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(location, forecast_date) DO UPDATE SET
            max_temp=excluded.max_temp,
            last_updated_at=excluded.last_updated_at
        """, data_to_insert)
        conn.commit()

def insert_observations(observation_data):
    """
    Inserts new observation data.
    observation_data should be a list of tuples: (location, observation_datetime, air_temp)
    """
    if not observation_data:
        logging.info("No observation data to insert.")
        return

    logging.info(f"Inserting {len(observation_data)} observation records.")
    now = datetime.utcnow().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        data_to_insert = [
            (rec['location'], rec['observation_datetime'], rec['air_temp'], now)
            for rec in observation_data
        ]
        cursor.executemany("""
        INSERT INTO observations (location, observation_datetime, air_temp, last_updated_at)
        VALUES (?, ?, ?, ?)
        """, data_to_insert)
        conn.commit()

def get_comparison_data(location, date_str):
    """
    Retrieves forecast and observation data for a specific location and date.
    """
    logging.info(f"Fetching comparison data for {location} on {date_str}")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get forecast for the specific date
        cursor.execute(
            "SELECT max_temp FROM forecasts WHERE location = ? AND forecast_date = ?",
            (location, date_str)
        )
        forecast = cursor.fetchone()
        
        # Get all observations for that day
        cursor.execute(
            "SELECT air_temp, observation_datetime FROM observations WHERE location = ? AND date(observation_datetime) = ?",
            (location, date_str)
        )
        observations = cursor.fetchall()
        
        return forecast, observations

def get_available_locations():
    """Gets a list of unique locations from the forecasts table."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT location FROM forecasts ORDER BY location ASC")
        locations = [row['location'] for row in cursor.fetchall()]
        if "Dunalley (Henry anson)" not in locations:
            locations.append("Dunalley (Henry anson)")
        return sorted(locations)

def cleanup_old_data():
    """Removes records older than 14 days."""
    logging.info("Cleaning up old data (older than 14 days)...")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        res_f = cursor.execute("DELETE FROM forecasts WHERE date(last_updated_at) < date('now', '-14 days')")
        logging.info(f"Deleted {res_f.rowcount} old forecast records.")
        
        res_o = cursor.execute("DELETE FROM observations WHERE date(last_updated_at) < date('now', '-14 days')")
        logging.info(f"Deleted {res_o.rowcount} old observation records.")
        
        conn.commit()