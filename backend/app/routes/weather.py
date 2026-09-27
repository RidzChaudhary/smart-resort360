"""
Weather API routes for real-time weather data and forecasting.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional

from app.database.connection import get_db
from app.models import User
from app.utils.auth import get_current_user
from app.services.weather_service import WeatherUnavailableError, get_weather_service

router = APIRouter(prefix="/api/weather", tags=["Weather"])


@router.get("/current")
def get_current_weather(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current weather conditions.
    """
    weather_service = get_weather_service()
    try:
        current = weather_service.get_current_weather(db=db, resort_id=current_user.resort_id)
    except WeatherUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Weather data is temporarily unavailable") from exc

    return {
        "current": current,
        "timestamp": current["timestamp"]
    }


@router.get("/forecast")
def get_weather_forecast(
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get hourly weather forecast.
    """
    if hours < 1 or hours > 48:
        raise HTTPException(status_code=400, detail="Hours must be between 1 and 48")

    weather_service = get_weather_service()
    try:
        forecast = weather_service.get_hourly_forecast(hours, db=db, resort_id=current_user.resort_id)
    except WeatherUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Weather data is temporarily unavailable") from exc

    return {
        "forecast": forecast,
        "hours": len(forecast)
    }


@router.get("/snapshot")
def get_weather_snapshot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get complete weather snapshot with current conditions and forecast.
    """
    weather_service = get_weather_service()

    try:
        current = weather_service.get_current_weather(db=db, resort_id=current_user.resort_id)
        forecast = weather_service.get_hourly_forecast(24, db=db, resort_id=current_user.resort_id)
        risk_window = weather_service.get_high_risk_window(db=db, resort_id=current_user.resort_id)
    except WeatherUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Weather data is temporarily unavailable") from exc

    return {
        "current": current,
        "forecast": forecast,
        "high_risk_window": risk_window,
        "is_demo": current.get("is_demo", False)
    }


@router.get("/risk-analysis")
def get_weather_risk_analysis(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get weather risk analysis for operational planning.
    """
    weather_service = get_weather_service()

    try:
        current = weather_service.get_current_weather(db=db, resort_id=current_user.resort_id)
        risk_window = weather_service.get_high_risk_window(db=db, resort_id=current_user.resort_id)
    except WeatherUnavailableError as exc:
        raise HTTPException(status_code=503, detail="Weather data is temporarily unavailable") from exc

    # Determine overall risk level
    if risk_window and risk_window["risk_score"] >= 70:
        risk_level = "HIGH"
    elif risk_window and risk_window["risk_score"] >= 50:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "risk_level": risk_level,
        "current_condition": current["condition"],
        "temperature_c": current["temperature_c"],
        "rain_probability": risk_window["rain_probability"] if risk_window else 0,
        "wind_speed_kmh": current["wind_speed_kmh"],
        "high_risk_window": risk_window,
        "recommendation": _get_weather_recommendation(risk_level, risk_window)
    }


def _get_weather_recommendation(risk_level: str, risk_window: Optional[Dict[str, Any]]) -> str:
    """Generate weather-based operational recommendation."""
    if risk_level == "HIGH" and risk_window:
        return (
            f"High weather risk detected at hour {risk_window['start_hour']}. "
            f"{risk_window['rain_probability']}% rain probability with "
            f"{risk_window['precipitation_mm']}mm precipitation expected. "
            "Review outdoor events and prepare contingency plans."
        )
    elif risk_level == "MEDIUM" and risk_window:
        return (
            f"Moderate weather risk expected. "
            f"{risk_window['rain_probability']}% rain probability. "
            "Monitor conditions for outdoor activities."
        )
    else:
        return "No significant weather risks detected for the next 24 hours."
