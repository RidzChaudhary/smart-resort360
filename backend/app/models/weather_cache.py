"""
WeatherCache model – persists last-fetched weather data so we can
serve a stale-but-valid response when the external API is unavailable.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean, ForeignKey
from datetime import datetime
from app.database.connection import Base


class WeatherCache(Base):
    __tablename__ = "weather_cache"

    id = Column(Integer, primary_key=True, index=True)
    resort_id = Column(Integer, ForeignKey("resorts.id"), nullable=False, index=True)

    # Fetched time
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Core weather fields
    temperature_c = Column(Float, nullable=True)
    apparent_temperature_c = Column(Float, nullable=True)
    weather_code = Column(Integer, nullable=True)             # WMO code
    condition = Column(String(100), nullable=True)            # "Light Rain", "Clear Sky"
    precipitation_mm = Column(Float, nullable=True)
    rain_probability = Column(Float, nullable=True)           # 0–100
    wind_speed_kmh = Column(Float, nullable=True)
    wind_gusts_kmh = Column(Float, nullable=True)
    humidity_pct = Column(Float, nullable=True)

    # Latitude/longitude used for the query
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Hourly forecast stored as JSON
    hourly_forecast = Column(JSON, nullable=True)

    # Flag: was this data actually fetched from the API or is it demo/fallback?
    is_live = Column(Boolean, default=True, nullable=False)
    is_demo = Column(Boolean, default=False, nullable=False)

    provider = Column(String(50), default="open_meteo")
