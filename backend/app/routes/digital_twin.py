"""
Digital Twin API routes for operational simulation and what-if analysis.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from app.database.connection import get_db
from app.models import User
from app.utils.auth import require_role
from app.services.digital_twin import create_digital_twin
from app.services.data_fusion import get_operational_snapshot
from app.services.impact_propagation import analyze_weather_impact

router = APIRouter(prefix="/api/digital-twin", tags=["Digital Twin"])


class WeatherSimulationRequest(BaseModel):
    """Request model for weather simulation."""
    rain_probability: Optional[float] = Field(None, ge=0, le=100, description="Rain probability (0-100%)")
    rain_intensity_mm: Optional[float] = Field(None, ge=0, le=50, description="Rain intensity (mm/hour)")
    wind_speed_kmh: Optional[float] = Field(None, ge=0, le=150, description="Wind speed (km/h)")
    duration_hours: Optional[int] = Field(None, ge=1, le=24, description="Storm duration (hours)")


@router.get("/state")
def get_digital_twin_state(
    current_user: User = Depends(require_role(["MANAGER", "DEPARTMENT_HEAD"])),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current Digital Twin state representing resort operations.
    Read-only snapshot that doesn't modify production database.
    """
    twin = create_digital_twin(db, current_user.resort_id)
    state = twin.get_current_state()

    return {
        "digital_twin": state.to_dict(),
        "snapshot_time": state.timestamp
    }


@router.get("/operational-snapshot")
def get_operational_snapshot_endpoint(
    current_user: User = Depends(require_role(["MANAGER", "DEPARTMENT_HEAD"])),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get unified operational snapshot combining resort data + weather.
    This is the foundation for all AI/Digital Twin analysis.
    """
    snapshot = get_operational_snapshot(db, current_user.resort_id)
    return snapshot


@router.post("/simulate")
def simulate_weather_impact(
    request: WeatherSimulationRequest,
    current_user: User = Depends(require_role(["MANAGER"])),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Run what-if simulation with hypothetical weather conditions.
    Returns predicted impact WITHOUT modifying production database.
    """
    # Create Digital Twin
    twin = create_digital_twin(db, current_user.resort_id)

    # Get current state for comparison
    current_state = twin.get_current_state().to_dict()

    # Run simulation with new weather parameters
    simulated_state = twin.simulate_weather_change(
        rain_probability=request.rain_probability,
        rain_intensity_mm=request.rain_intensity_mm,
        wind_speed_kmh=request.wind_speed_kmh,
        duration_hours=request.duration_hours
    )

    # Analyze impact on simulated state
    impact_analysis = analyze_weather_impact(simulated_state)

    # Calculate differences
    current_weather = current_state["weather"]["current"]
    simulated_weather = simulated_state["weather"]["current"]

    weather_delta = {
        "rain_probability": {
            "current": current_weather.get("rain_probability", 0),
            "simulated": simulated_weather.get("rain_probability", 0),
            "change": simulated_weather.get("rain_probability", 0) - current_weather.get("rain_probability", 0)
        },
        "precipitation_mm": {
            "current": current_weather.get("precipitation_mm", 0),
            "simulated": simulated_weather.get("precipitation_mm", 0),
            "change": simulated_weather.get("precipitation_mm", 0) - current_weather.get("precipitation_mm", 0)
        },
        "wind_speed_kmh": {
            "current": current_weather.get("wind_speed_kmh", 0),
            "simulated": simulated_weather.get("wind_speed_kmh", 0),
            "change": simulated_weather.get("wind_speed_kmh", 0) - current_weather.get("wind_speed_kmh", 0)
        }
    }

    return {
        "simulation": {
            "parameters": request.dict(exclude_none=True),
            "timestamp": simulated_state["_simulation_timestamp"]
        },
        "current_state": {
            "weather": current_weather,
            "events_count": len(current_state["events"])
        },
        "simulated_state": {
            "weather": simulated_weather,
            "events_count": len(simulated_state["events"])
        },
        "weather_delta": weather_delta,
        "impact_analysis": impact_analysis,
        "summary": _generate_simulation_summary(impact_analysis, weather_delta)
    }


@router.get("/impact-analysis")
def get_impact_analysis(
    current_user: User = Depends(require_role(["MANAGER", "DEPARTMENT_HEAD"])),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Analyze current weather impact on resort operations.
    """
    # Get current Digital Twin state
    twin = create_digital_twin(db, current_user.resort_id)
    state = twin.get_current_state().to_dict()

    # Run impact analysis
    impact = analyze_weather_impact(state)

    return {
        "impact_analysis": impact,
        "current_weather": state["weather"]["current"],
        "timestamp": state["timestamp"]
    }


def _generate_simulation_summary(
    impact: Dict[str, Any],
    delta: Dict[str, Any]
) -> str:
    """Generate human-readable simulation summary."""
    risk = impact["risk_level"]
    affected = impact["affected_events_count"]
    guests = impact["affected_guests"]

    rain_change = delta["rain_probability"]["change"]

    if affected > 0:
        return (
            f"{risk} risk scenario: {affected} event(s) affecting {guests} guests. "
            f"Rain probability {'increased' if rain_change > 0 else 'decreased'} by {abs(rain_change):.0f}%. "
            f"{len(impact['affected_departments'])} department(s) require contingency actions."
        )
    else:
        return (
            f"{risk} risk scenario with no immediate operational impact. "
            f"All events can proceed as scheduled."
        )
