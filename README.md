# SalterWaterRiver_weather_forecast
# BoM Weather Comparison App

A simple Python application that fetches weather forecasts and observations from the Bureau of Meteorology (BoM), stores them, and displays a comparison in a web app.

Built with Python, Streamlit, and SQLite.

---

## Features

-   Fetches Tasmania précis forecasts (IDT16710) from the BoM FTP server.
-   Fetches live observation data for Dunalley (IDT60801.94951).
-   Stores data in a local SQLite database.
-   Forecast data is updated using an "upsert" operation.
-   Data is automatically purged after 14 days.
-   A web interface built with Streamlit to view and compare the data with filters.

---

