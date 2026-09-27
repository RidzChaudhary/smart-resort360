"""
Digital Twin - Virtual representation of resort operational state.
Enables what-if simulation without modifying production database.
"""
import copy
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.services.data_fusion import get_operational_snapshot


class DigitalTwinState:
    """
    Immutable snapshot representing resort's operational state.
    Used for simulation without touching real database.
    """

    def __init__(self, operational_snapshot: Dict[str, Any]):
        """Initialize Digital Twin from OperationalSnapshot."""
        self.timestamp = operational_snapshot["timestamp"]
        self.resort_id = operational_snapshot["resort_id"]

        # Deep copy to ensure immutability
        self.resort_state = copy.deepcopy(operational_snapshot["resort_state"])
        self.staff_availability = copy.deepcopy(operational_snapshot["staff_availability"])
        self.events = copy.deepcopy(operational_snapshot["events"])
        self.operational_issues = copy.deepcopy(operational_snapshot["operational_issues"])
        self.inventory_at_risk = copy.deepcopy(operational_snapshot["inventory_at_risk"])
        self.weather = copy.deepcopy(operational_snapshot["weather"])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamp": self.timestamp,
            "resort_id": self.resort_id,
            "resort_state": self.resort_state,
            "staff_availability": self.staff_availability,
            "events": self.events,
            "operational_issues": self.operational_issues,
            "inventory_at_risk": self.inventory_at_risk,
            "weather": self.weather
        }


class DigitalTwin:
    """
    Digital Twin system for resort operations.
    Enables read-only analysis and what-if simulation.
    """

    def __init__(self, db: Session, resort_id: int):
        self.db = db
        self.resort_id = resort_id
        self._current_state: Optional[DigitalTwinState] = None

    def refresh_state(self) -> DigitalTwinState:
        """Refresh Digital Twin state from current operational snapshot."""
        snapshot = get_operational_snapshot(self.db, self.resort_id)
        self._current_state = DigitalTwinState(snapshot)
        return self._current_state

    def get_current_state(self) -> DigitalTwinState:
        """Get current Digital Twin state (refreshes if not available)."""
        if self._current_state is None:
            self.refresh_state()
        return self._current_state

    def simulate_weather_change(
        self,
        rain_probability: Optional[float] = None,
        rain_intensity_mm: Optional[float] = None,
        wind_speed_kmh: Optional[float] = None,
        duration_hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Simulate impact of weather change on resort operations.
        Returns simulated state WITHOUT modifying production database.
        """
        # Get current state
        current_state = self.get_current_state()

        # Create simulation state (deep copy)
        sim_state = copy.deepcopy(current_state.to_dict())

        # Apply hypothetical weather changes
        if rain_probability is not None:
            sim_state["weather"]["current"]["rain_probability"] = rain_probability

        if rain_intensity_mm is not None:
            sim_state["weather"]["current"]["precipitation_mm"] = rain_intensity_mm
            sim_state["weather"]["current"]["rain_mm"] = rain_intensity_mm

        if wind_speed_kmh is not None:
            sim_state["weather"]["current"]["wind_speed_kmh"] = wind_speed_kmh

        # Update simulated hourly forecast if duration provided
        if duration_hours and sim_state["weather"].get("hourly_forecast"):
            for i in range(min(duration_hours, len(sim_state["weather"]["hourly_forecast"]))):
                if rain_probability is not None:
                    sim_state["weather"]["hourly_forecast"][i]["rain_probability"] = rain_probability
                if rain_intensity_mm is not None:
                    sim_state["weather"]["hourly_forecast"][i]["precipitation_mm"] = rain_intensity_mm
                if wind_speed_kmh is not None:
                    sim_state["weather"]["hourly_forecast"][i]["wind_speed_kmh"] = wind_speed_kmh

        # Mark as simulation
        sim_state["_is_simulation"] = True
        sim_state["_simulation_timestamp"] = datetime.utcnow().isoformat()

        return sim_state


def create_digital_twin(db: Session, resort_id: int) -> DigitalTwin:
    """Factory function to create Digital Twin instance."""
    return DigitalTwin(db, resort_id)
