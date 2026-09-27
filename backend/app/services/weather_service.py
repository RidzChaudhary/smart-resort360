"""
Real-time weather service using Open-Meteo API.
Provides current weather, hourly forecasts, caching, and DB-backed persistence.
"""
import os
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import json
import logging
from sqlalchemy.orm import Session

APP_ENV = os.getenv("APP_ENV", "development").strip().casefold()
MAX_STALE_WEATHER_HOURS = int(os.getenv("WEATHER_MAX_STALE_HOURS", "24"))
logger = logging.getLogger(__name__)


class WeatherUnavailableError(RuntimeError):
    """Raised when neither live nor recent real weather data is available."""


class WeatherService:
    """
    Real-time weather integration with Open-Meteo API.
    Includes memory caching, DB persistence, and graceful fallback behavior.
    """

    # Azure Palm Resort coordinates (location: Goa, India)
    DEFAULT_LATITUDE = 15.2993
    DEFAULT_LONGITUDE = 73.9876

    # Open-Meteo API endpoint
    API_BASE_URL = "https://api.open-meteo.com/v1/forecast"

    # Cache duration in minutes
    CACHE_MINUTES = int(os.getenv("WEATHER_CACHE_MINUTES", "10"))

    # Demo mode flag
    DEMO_MODE = os.getenv("DEMO_WEATHER_MODE", "false").lower() == "true"
    APP_ENV = APP_ENV

    if APP_ENV == "production" and DEMO_MODE:
        raise RuntimeError("DEMO_WEATHER_MODE cannot be enabled in production")

    def __init__(self):
        self._cache = {}
        self._cache_timestamp = None
        self._cache_key = None

    def _is_cache_valid(self) -> bool:
        """Check if in-memory cached data is still valid."""
        if not self._cache_timestamp:
            return False
        elapsed = datetime.utcnow() - self._cache_timestamp
        return elapsed.total_seconds() < (self.CACHE_MINUTES * 60)

    def _fetch_from_api(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """Fetch weather data from Open-Meteo API using standard library."""
        try:
            params = {
                "latitude": str(latitude),
                "longitude": str(longitude),
                "current": "temperature_2m,relative_humidity_2m,precipitation,rain,weather_code,wind_speed_10m,wind_gusts_10m",
                "hourly": "temperature_2m,precipitation_probability,precipitation,rain,weather_code,wind_speed_10m",
                "temperature_unit": "celsius",
                "wind_speed_unit": "kmh",
                "precipitation_unit": "mm",
                "timezone": "auto",
                "forecast_days": "2"
            }

            url = f"{self.API_BASE_URL}?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={"User-Agent": "SmartResort360/1.0"})
            with urllib.request.urlopen(req, timeout=6) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    return data
            return None
        except Exception as e:
            print(f"⚠️ Weather API fetch failed: {e}")
            return None


    def _get_weather_condition(self, weather_code: int) -> str:
        """Convert WMO weather code to human-readable condition."""
        weather_map = {
            0: "Clear Sky",
            1: "Mainly Clear",
            2: "Partly Cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing Rime Fog",
            51: "Light Drizzle",
            53: "Moderate Drizzle",
            55: "Dense Drizzle",
            61: "Slight Rain",
            63: "Moderate Rain",
            65: "Heavy Rain",
            71: "Slight Snow",
            73: "Moderate Snow",
            75: "Heavy Snow",
            80: "Slight Rain Showers",
            81: "Moderate Rain Showers",
            82: "Violent Rain Showers",
            85: "Slight Snow Showers",
            86: "Heavy Snow Showers",
            95: "Thunderstorm",
            96: "Thunderstorm with Slight Hail",
            99: "Thunderstorm with Heavy Hail"
        }
        return weather_map.get(weather_code, "Partly Cloudy")

    def _get_demo_weather(self) -> Dict[str, Any]:
        """Return clearly marked demo/simulated weather data."""
        now = datetime.utcnow()

        # Realistic demo scenario: storm approaching in 3-6 hours (85% rain probability)
        demo_hourly = []
        for hour_offset in range(24):
            hour_time = now + timedelta(hours=hour_offset)

            if 3 <= hour_offset <= 6:
                rain_prob = 70 + (hour_offset - 3) * 5  # 70%, 75%, 80%, 85%
                precip = 2.5 + (hour_offset - 3) * 1.5
                temp = 24.5 - (hour_offset - 3) * 0.5
                wind = 28 + (hour_offset - 3) * 6
                weather_code = 65 if hour_offset >= 5 else 63
            elif hour_offset > 6:
                rain_prob = max(20, 85 - (hour_offset - 6) * 10)
                precip = max(0.0, 6.0 - (hour_offset - 6) * 1.0)
                temp = 24.0
                wind = max(15, 35 - (hour_offset - 6) * 3)
                weather_code = 61
            else:
                rain_prob = 15 + hour_offset * 10
                precip = 0.0
                temp = 27.5
                wind = 14
                weather_code = 2

            demo_hourly.append({
                "time": hour_time.isoformat(),
                "temperature_2m": temp,
                "precipitation_probability": min(rain_prob, 95),
                "precipitation": round(precip, 1),
                "rain": round(precip, 1),
                "weather_code": weather_code,
                "wind_speed_10m": wind
            })

        return {
            "current": {
                "temperature_2m": 27.5,
                "relative_humidity_2m": 68,
                "precipitation": 0.0,
                "rain": 0.0,
                "weather_code": 2,
                "wind_speed_10m": 16,
                "wind_gusts_10m": 24,
                "time": now.isoformat()
            },
            "hourly": demo_hourly,
            "latitude": self.DEFAULT_LATITUDE,
            "longitude": self.DEFAULT_LONGITUDE,
            "_demo_mode": True
        }

    def _persist_to_db(self, db: Session, resort_id: int, snapshot: Dict[str, Any], is_live: bool):
        """Save weather snapshot into database cache."""
        try:
            from app.models.weather_cache import WeatherCache
            current = snapshot.get("current", {})
            hourly = snapshot.get("hourly", [])
            w_code = current.get("weather_code", 0)

            # Rain probability from first hourly entry if not in current
            rain_prob = 0
            if hourly and isinstance(hourly, list) and len(hourly) > 0:
                rain_prob = hourly[0].get("precipitation_probability", 0)

            cache_record = WeatherCache(
                resort_id=resort_id,
                fetched_at=datetime.utcnow(),
                temperature_c=current.get("temperature_2m"),
                weather_code=w_code,
                condition=self._get_weather_condition(w_code),
                precipitation_mm=current.get("precipitation"),
                rain_probability=float(rain_prob),
                wind_speed_kmh=current.get("wind_speed_10m"),
                wind_gusts_kmh=current.get("wind_gusts_10m"),
                humidity_pct=current.get("relative_humidity_2m"),
                latitude=snapshot.get("latitude", self.DEFAULT_LATITUDE),
                longitude=snapshot.get("longitude", self.DEFAULT_LONGITUDE),
                hourly_forecast=hourly[:24] if isinstance(hourly, list) else None,
                is_live=is_live,
                is_demo=snapshot.get("_demo_mode", False),
                provider="open_meteo"
            )
            db.add(cache_record)
            db.commit()
        except Exception:
            logger.exception("Unable to persist weather cache")

    def _load_recent_live_cache(self, db: Optional[Session], resort_id: Optional[int]) -> Optional[Dict[str, Any]]:
        if db is None or resort_id is None:
            return None
        try:
            from app.models.weather_cache import WeatherCache
            record = db.query(WeatherCache).filter(
                WeatherCache.resort_id == resort_id,
                WeatherCache.is_live.is_(True),
                WeatherCache.is_demo.is_(False),
            ).order_by(WeatherCache.fetched_at.desc()).first()
        except Exception:
            logger.exception("Unable to read persisted weather cache")
            return None
        if record is None:
            return None

        age_minutes = max(0, int((datetime.utcnow() - record.fetched_at).total_seconds() / 60))
        if age_minutes > MAX_STALE_WEATHER_HOURS * 60:
            return None
        return {
            "current": {
                "temperature_2m": record.temperature_c,
                "relative_humidity_2m": record.humidity_pct,
                "precipitation": record.precipitation_mm,
                "rain": record.precipitation_mm,
                "weather_code": record.weather_code,
                "wind_speed_10m": record.wind_speed_kmh,
                "wind_gusts_10m": record.wind_gusts_kmh,
                "time": record.fetched_at.isoformat(),
            },
            "hourly": record.hourly_forecast or [],
            "latitude": record.latitude or self.DEFAULT_LATITUDE,
            "longitude": record.longitude or self.DEFAULT_LONGITUDE,
            "_demo_mode": False,
            "_stale": True,
            "_data_age_minutes": age_minutes,
        }

    def get_weather_snapshot(
        self,
        db: Optional[Session] = None,
        resort_id: Optional[int] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Get complete weather snapshot with current conditions and forecast.
        Uses cached data when available and valid.
        """
        lat = latitude or self.DEFAULT_LATITUDE
        lon = longitude or self.DEFAULT_LONGITUDE
        cache_key = (resort_id, lat, lon)

        # Check in-memory cache first
        if self._is_cache_valid() and self._cache and self._cache_key == cache_key:
            return self._cache

        is_live = False
        if self.DEMO_MODE:
            weather_data = self._get_demo_weather()
        else:
            weather_data = self._fetch_from_api(lat, lon)
            if weather_data:
                is_live = True
                weather_data["_demo_mode"] = False
                weather_data["_stale"] = False
            else:
                weather_data = self._load_recent_live_cache(db, resort_id)
                if weather_data is None:
                    if self.APP_ENV == "production":
                        raise WeatherUnavailableError("Live weather and recent cached weather are unavailable")
                    logger.warning("Weather provider unavailable; serving explicitly labeled development demo weather")
                    weather_data = self._get_demo_weather()

        # Update in-memory cache
        self._cache = weather_data
        self._cache_timestamp = datetime.utcnow()
        self._cache_key = cache_key

        # Optionally persist to DB
        if db and resort_id and not weather_data.get("_stale"):
            self._persist_to_db(db, resort_id, weather_data, is_live)

        return weather_data

    def _normalize_hourly(self, hourly_data: Any) -> List[Dict[str, Any]]:
        """Normalize hourly data to list-of-dicts format regardless of API source."""
        if isinstance(hourly_data, list):
            return hourly_data
        if isinstance(hourly_data, dict):
            times = hourly_data.get("time", [])
            temps = hourly_data.get("temperature_2m", [])
            rain_probs = hourly_data.get("precipitation_probability", [])
            precips = hourly_data.get("precipitation", [])
            rains = hourly_data.get("rain", [])
            codes = hourly_data.get("weather_code", [])
            winds = hourly_data.get("wind_speed_10m", [])

            normalized = []
            for i in range(len(times)):
                normalized.append({
                    "time": times[i] if i < len(times) else "",
                    "temperature_2m": temps[i] if i < len(temps) else 25.0,
                    "precipitation_probability": rain_probs[i] if i < len(rain_probs) else 0,
                    "precipitation": precips[i] if i < len(precips) else 0.0,
                    "rain": rains[i] if i < len(rains) else 0.0,
                    "weather_code": codes[i] if i < len(codes) else 0,
                    "wind_speed_10m": winds[i] if i < len(winds) else 10.0
                })
            return normalized
        return []

    def get_current_weather(self, db: Optional[Session] = None, resort_id: Optional[int] = None) -> Dict[str, Any]:
        """Get current weather conditions formatted."""
        snapshot = self.get_weather_snapshot(db=db, resort_id=resort_id)
        current = snapshot.get("current", {})
        hourly = self._normalize_hourly(snapshot.get("hourly", []))

        # Get current rain prob from first hour or current
        rain_prob = 0
        if hourly and len(hourly) > 0:
            rain_prob = hourly[0].get("precipitation_probability", 0)

        w_code = current.get("weather_code", 0)
        return {
            "temperature_c": current.get("temperature_2m", 0),
            "humidity": current.get("relative_humidity_2m", 0),
            "precipitation_mm": current.get("precipitation", 0),
            "rain_mm": current.get("rain", 0),
            "rain_probability": rain_prob,
            "weather_code": w_code,
            "condition": self._get_weather_condition(w_code),
            "wind_speed_kmh": current.get("wind_speed_10m", 0),
            "wind_gusts_kmh": current.get("wind_gusts_10m", 0),
            "timestamp": current.get("time", datetime.utcnow().isoformat()),
            "is_demo": snapshot.get("_demo_mode", False),
            "is_stale": snapshot.get("_stale", False),
            "data_age_minutes": snapshot.get("_data_age_minutes", 0),
        }

    def get_hourly_forecast(self, hours: int = 24, db: Optional[Session] = None, resort_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get hourly weather forecast."""
        snapshot = self.get_weather_snapshot(db=db, resort_id=resort_id)
        hourly_data = self._normalize_hourly(snapshot.get("hourly", []))

        forecast = []
        for i, hour in enumerate(hourly_data[:hours]):
            w_code = hour.get("weather_code", 0)
            forecast.append({
                "hour": i,
                "time": hour.get("time", ""),
                "temperature_c": hour.get("temperature_2m", 0),
                "rain_probability": hour.get("precipitation_probability", 0),
                "precipitation_mm": hour.get("precipitation", 0),
                "rain_mm": hour.get("rain", 0),
                "weather_code": w_code,
                "condition": self._get_weather_condition(w_code),
                "wind_speed_kmh": hour.get("wind_speed_10m", 0)
            })

        return forecast


    def get_high_risk_window(self, db: Optional[Session] = None, resort_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Identify the highest risk weather window in the next 24 hours.
        Returns None if no significant risk detected.
        """
        forecast = self.get_hourly_forecast(24, db=db, resort_id=resort_id)

        max_risk_score = 0
        risk_window = None

        for i, hour in enumerate(forecast):
            rain_prob = hour["rain_probability"]
            precip = hour["precipitation_mm"]
            wind = hour["wind_speed_kmh"]

            # Risk formula: weighted combination of factors
            risk_score = (rain_prob * 0.5) + (min(precip * 10, 30) * 0.3) + (min(wind / 2, 20) * 0.2)

            if risk_score > max_risk_score:
                max_risk_score = risk_score
                risk_window = {
                    "start_hour": i,
                    "time": hour["time"],
                    "risk_score": round(risk_score, 1),
                    "rain_probability": rain_prob,
                    "precipitation_mm": precip,
                    "wind_speed_kmh": wind,
                    "condition": hour["condition"]
                }

        if risk_window and risk_window["risk_score"] >= 40:
            return risk_window

        return None


# Module-level defaults and Singleton instance
DEFAULT_LATITUDE = WeatherService.DEFAULT_LATITUDE
DEFAULT_LONGITUDE = WeatherService.DEFAULT_LONGITUDE

_weather_service = None

def get_weather_service() -> WeatherService:
    """Get singleton weather service instance."""
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService()
    return _weather_service


def get_weather_snapshot(
    db: Optional[Session] = None,
    resort_id: Optional[int] = None,
    lat: float = DEFAULT_LATITUDE,
    lon: float = DEFAULT_LONGITUDE
) -> Dict[str, Any]:
    """Convenience module function."""
    service = get_weather_service()
    return service.get_weather_snapshot(db=db, resort_id=resort_id, latitude=lat, longitude=lon)
