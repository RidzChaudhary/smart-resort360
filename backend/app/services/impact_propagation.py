"""
Impact Propagation Engine - Determines how weather affects resort operations.
Uses deterministic rules and continuous scaling to calculate realistic operational impact.

Phase 1 Enhancement:
- Handles both ResortEvent (OUTDOOR/INDOOR) and ResortActivity (outdoor/indoor)
- Uses the normalised `outdoor` boolean field set by data_fusion
- Checks indoor_alternative from ResortEvent if available
- Continuous proportional impact scaling to prevent abrupt step-function jumps
"""
from typing import Dict, Any, List, Optional
from datetime import datetime


class ImpactPropagationEngine:
    """
    Analyzes how weather conditions propagate through resort operations.
    All impact calculations are deterministic, smooth, and explainable.
    """

    # Risk thresholds
    RAIN_THRESHOLD_ADVISORY = 25   # % probability
    RAIN_THRESHOLD_MEDIUM = 45     # % probability
    RAIN_THRESHOLD_HIGH = 65       # % probability
    RAIN_THRESHOLD_CRITICAL = 80   # % probability

    RAIN_INTENSITY_HIGH = 5.0      # mm/hour
    WIND_THRESHOLD_HIGH = 40       # km/h
    WIND_THRESHOLD_CRITICAL = 60

    def __init__(self):
        pass

    def _calculate_weather_risk_score(self, weather: Dict[str, Any]) -> float:
        """
        Calculate overall weather risk score (0-100).
        Formula: weighted combination of rain, wind, and intensity.
        """
        current = weather.get("current", {})

        rain_prob = current.get("rain_probability", 0)
        precipitation = current.get("precipitation_mm", 0)
        wind_speed = current.get("wind_speed_kmh", 0)

        # Risk components
        rain_risk = rain_prob * 0.5               # Rain probability contributes 50%
        intensity_risk = min(precipitation * 5, 30) * 0.3  # Intensity contributes 30%
        wind_risk = min(wind_speed / 2, 20) * 0.2           # Wind contributes 20%

        total_risk = rain_risk + intensity_risk + wind_risk
        return round(total_risk, 1)

    def _is_event_outdoor(self, event: Dict[str, Any]) -> bool:
        """
        Normalise outdoor detection.
        Phase 1 ResortEvent uses location_type = "OUTDOOR".
        Legacy ResortActivity may use "outdoor" or the `outdoor` bool.
        """
        if "outdoor" in event:
            return bool(event["outdoor"])
        loc_type = str(event.get("location_type", "")).upper()
        return loc_type == "OUTDOOR"

    def _identify_affected_events(
        self,
        events: List[Dict[str, Any]],
        weather: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Identify events affected by weather conditions.
        Uses realistic, continuous scaling based on weather severity to prevent sudden jumps.
        """
        current = weather.get("current", {})
        rain_prob = current.get("rain_probability", 0)
        precipitation = current.get("precipitation_mm", 0)
        wind_speed = current.get("wind_speed_kmh", 0)

        # Composite weather severity metric (0-100)
        severity = max(rain_prob, (precipitation * 5), (wind_speed * 0.8))

        affected_events = []

        for event in events:
            is_outdoor = self._is_event_outdoor(event)
            is_weather_dependent = event.get("weather_dependent", False)

            if not (is_outdoor and is_weather_dependent):
                continue

            expected_guests = event.get("expected_guests", 0)

            if severity >= self.RAIN_THRESHOLD_CRITICAL:
                impact_level = "CRITICAL"
                impact_reason = f"{rain_prob:.0f}% rain probability ({precipitation:.1f}mm/h) – full event relocation required"
                affected_guests = expected_guests
            elif severity >= self.RAIN_THRESHOLD_HIGH:
                impact_level = "HIGH"
                impact_reason = f"{rain_prob:.0f}% rain probability – high disruption risk, prepare indoor backup"
                # Smooth scaling between 70% and 100% of guests
                ratio = 0.70 + 0.30 * ((severity - self.RAIN_THRESHOLD_HIGH) / (self.RAIN_THRESHOLD_CRITICAL - self.RAIN_THRESHOLD_HIGH))
                affected_guests = min(expected_guests, max(1, round(expected_guests * ratio)))
            elif severity >= self.RAIN_THRESHOLD_MEDIUM:
                impact_level = "MEDIUM"
                impact_reason = f"{rain_prob:.0f}% rain probability – moderate weather risk, partial indoor seating advisory"
                # Smooth scaling between 35% and 70% of guests
                ratio = 0.35 + 0.35 * ((severity - self.RAIN_THRESHOLD_MEDIUM) / (self.RAIN_THRESHOLD_HIGH - self.RAIN_THRESHOLD_MEDIUM))
                affected_guests = min(expected_guests, max(1, round(expected_guests * ratio)))
            elif severity >= self.RAIN_THRESHOLD_ADVISORY:
                impact_level = "LOW"
                impact_reason = f"{rain_prob:.0f}% rain probability – slight weather risk, monitor conditions"
                # Smooth scaling between 10% and 35% of guests
                ratio = 0.10 + 0.25 * ((severity - self.RAIN_THRESHOLD_ADVISORY) / (self.RAIN_THRESHOLD_MEDIUM - self.RAIN_THRESHOLD_ADVISORY))
                affected_guests = min(expected_guests, max(1, round(expected_guests * ratio)))
            else:
                impact_level = "NONE"
                impact_reason = "Weather conditions optimal for outdoor operations"
                affected_guests = 0

            if impact_level != "NONE":
                affected_events.append({
                    **event,
                    "impact_level": impact_level,
                    "impact_reason": impact_reason,
                    "affected_guests": affected_guests,
                    "recommended_action": self._get_event_recommendation(event, severity)
                })

        return affected_events

    def _get_event_recommendation(self, event: Dict[str, Any], severity: float) -> str:
        """Generate specific recommendation for affected event based on severity."""
        name = event.get("name", "event")
        alt = event.get("indoor_alternative")

        if severity >= self.RAIN_THRESHOLD_CRITICAL:
            if alt:
                return f"Relocate '{name}' to {alt} immediately"
            return f"Relocate '{name}' to an available indoor venue immediately"
        elif severity >= self.RAIN_THRESHOLD_HIGH:
            if alt:
                return f"Prepare {alt} as indoor backup for '{name}'"
            return f"Prepare indoor backup for '{name}'"
        elif severity >= self.RAIN_THRESHOLD_MEDIUM:
            return f"Notify guests of potential weather advisory for '{name}' and prepare covered seating"
        elif severity >= self.RAIN_THRESHOLD_ADVISORY:
            return f"Monitor weather radar for '{name}'"
        return "No action required"

    def _identify_alternative_venues(
        self,
        affected_events: List[Dict[str, Any]],
        all_events: List[Dict[str, Any]]
    ) -> Dict[Any, Dict[str, Any]]:
        """
        Identify indoor alternative venues for affected outdoor events.
        Priority: indoor_alternative field (ResortEvent), then indoor events, then defaults.
        """
        indoor_venues = [
            e for e in all_events
            if not self._is_event_outdoor(e)
        ]

        default_alternatives = [
            {"name": "Palm Ballroom", "capacity": 80, "type": "INDOOR"},
            {"name": "Ocean View Conference Room", "capacity": 50, "type": "INDOOR"},
            {"name": "Garden Pavilion (Covered)", "capacity": 60, "type": "INDOOR"},
        ]

        alternatives = {}
        for event in affected_events:
            event_id = event.get("id")
            expected_guests = event.get("affected_guests", event.get("expected_guests", 0))

            if event.get("indoor_alternative"):
                alternatives[event_id] = {
                    "name": event["indoor_alternative"],
                    "capacity": event.get("indoor_alt_capacity"),
                    "latitude": event.get("indoor_alt_latitude"),
                    "longitude": event.get("indoor_alt_longitude"),
                    "type": "INDOOR",
                    "source": "resort_event",
                }
                continue

            suitable_venue = None
            for venue in indoor_venues:
                venue_capacity = venue.get("capacity", 0) or venue.get("available_slots", 0) or 0
                if venue_capacity >= expected_guests:
                    suitable_venue = {
                        "name": venue["name"],
                        "capacity": venue_capacity,
                        "type": "INDOOR",
                        "source": "event_list",
                    }
                    break

            if not suitable_venue:
                for alt in default_alternatives:
                    if alt["capacity"] >= expected_guests:
                        suitable_venue = {**alt, "source": "default"}
                        break

            if suitable_venue:
                alternatives[event_id] = suitable_venue

        return alternatives

    def _identify_affected_departments(
        self,
        affected_events: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Identify departments that need to respond to weather impact based on impact severity.
        """
        departments = set()

        for event in affected_events:
            level = event.get("impact_level", "NONE")
            if level in ("CRITICAL", "HIGH"):
                departments.update(["Food & Beverage", "Housekeeping", "Front Desk", "Maintenance"])
            elif level == "MEDIUM":
                departments.update(["Food & Beverage", "Front Desk"])
            elif level == "LOW":
                departments.update(["Front Desk"])

        return sorted(list(departments))

    def _calculate_guest_impact(self, affected_events: List[Dict[str, Any]]) -> int:
        """Calculate total number of guests affected."""
        return sum(event.get("affected_guests", event.get("expected_guests", 0)) for event in affected_events)

    def analyze_impact(self, digital_twin_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze weather impact on resort operations.
        Returns deterministic, realistic impact assessment.
        """
        weather = digital_twin_state.get("weather", {})
        events = digital_twin_state.get("events", [])

        if weather.get("available") is False:
            return {
                "risk_level": "UNKNOWN",
                "risk_score": None,
                "affected_events_count": 0,
                "affected_events": [],
                "affected_guests": 0,
                "affected_departments": [],
                "alternative_venues": {},
                "geospatial_markers": [],
                "weather_condition": "Unavailable",
                "analysis_timestamp": datetime.utcnow().isoformat(),
                "explanation": "Weather data is unavailable; no weather impact was inferred.",
                "data_available": False,
            }

        risk_score = self._calculate_weather_risk_score(weather)

        if risk_score >= 80:
            risk_level = "CRITICAL"
        elif risk_score >= 60:
            risk_level = "HIGH"
        elif risk_score >= 35:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        affected_events = self._identify_affected_events(events, weather)
        alternative_venues = self._identify_alternative_venues(affected_events, events)
        affected_departments = self._identify_affected_departments(affected_events)
        affected_guests = self._calculate_guest_impact(affected_events)

        geospatial_markers = []
        for ev in events:
            if ev.get("latitude") and ev.get("longitude"):
                marker_status = "NORMAL"
                if any(ae.get("id") == ev.get("id") for ae in affected_events):
                    marker_status = "AT_RISK" if risk_level in ("HIGH", "CRITICAL") else "AFFECTED"
                geospatial_markers.append({
                    "id": ev.get("id"),
                    "name": ev.get("name"),
                    "latitude": ev["latitude"],
                    "longitude": ev["longitude"],
                    "type": ev.get("location_type", "OUTDOOR"),
                    "status": marker_status,
                    "expected_guests": ev.get("expected_guests", 0),
                })
        for event_id, alt in alternative_venues.items():
            if alt.get("latitude") and alt.get("longitude"):
                geospatial_markers.append({
                    "id": f"alt_{event_id}",
                    "name": alt["name"],
                    "latitude": alt["latitude"],
                    "longitude": alt["longitude"],
                    "type": "INDOOR",
                    "status": "ALTERNATIVE",
                })

        impact_summary = {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "affected_events_count": len(affected_events),
            "affected_events": affected_events,
            "affected_guests": affected_guests,
            "affected_departments": affected_departments,
            "alternative_venues": alternative_venues,
            "geospatial_markers": geospatial_markers,
            "weather_condition": weather.get("current", {}).get("condition", "Unknown"),
            "analysis_timestamp": datetime.utcnow().isoformat()
        }

        if affected_events:
            impact_summary["explanation"] = (
                f"{risk_level} weather risk ({risk_score}/100). "
                f"{len(affected_events)} outdoor event(s) with {affected_guests} estimated guest(s) affected. "
                f"Contingency actions involving: {', '.join(affected_departments)}."
            )
        else:
            impact_summary["explanation"] = (
                f"{risk_level} weather risk ({risk_score}/100). No immediate operational impact detected."
            )

        return impact_summary


def analyze_weather_impact(digital_twin_state: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to analyze weather impact."""
    engine = ImpactPropagationEngine()
    return engine.analyze_impact(digital_twin_state)
