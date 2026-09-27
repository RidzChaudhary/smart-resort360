"""
Phase 1 Demo Seed – seeds ResortEvent and ResortLocation demo data.

Demo scenario:
  Resort: 100 rooms, 91% occupancy
  Event:  "Sunset Pool BBQ" at Outdoor Pool, 16:00–19:00
          Expected guests: 60
  Weather: 87% rain probability (served by Open-Meteo or demo fallback)
  Alternative: Palm Ballroom (capacity 80)

Run via: POST /api/demo/seed-phase1
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import Resort


# ─── Demo Location Data ──────────────────────────────────────────────────────
# Coordinates are clearly marked demo/approximate – not real resort precision.

DEMO_LOCATIONS = [
    {
        "name": "Outdoor Pool",
        "location_type": "POOL",
        "indoor": False,
        "latitude": 8.8935,
        "longitude": 76.6145,
        "capacity": 80,
        "description": "Main resort outdoor pool and event area",
    },
    {
        "name": "Palm Ballroom",
        "location_type": "BALLROOM",
        "indoor": True,
        "latitude": 8.8930,
        "longitude": 76.6140,
        "capacity": 80,
        "description": "Indoor banquet hall – primary wet-weather alternative",
    },
    {
        "name": "Beach Restaurant",
        "location_type": "RESTAURANT",
        "indoor": False,
        "latitude": 8.8940,
        "longitude": 76.6150,
        "capacity": 60,
        "description": "Open-air beachside restaurant",
    },
    {
        "name": "Garden Pavilion",
        "location_type": "GARDEN",
        "indoor": False,
        "latitude": 8.8928,
        "longitude": 76.6135,
        "capacity": 50,
        "description": "Landscaped garden – partially covered",
    },
    {
        "name": "Ocean View Conference Room",
        "location_type": "CONFERENCE",
        "indoor": True,
        "latitude": 8.8933,
        "longitude": 76.6142,
        "capacity": 50,
        "description": "Climate-controlled conference room overlooking the ocean",
    },
    {
        "name": "Reception Lobby",
        "location_type": "LOBBY",
        "indoor": True,
        "latitude": 8.8931,
        "longitude": 76.6138,
        "capacity": 100,
        "description": "Main lobby and reception area",
    },
]


# ─── Demo Event ───────────────────────────────────────────────────────────────

def _today_event_time(hour: int, minute: int = 0) -> datetime:
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return today.replace(hour=hour, minute=minute)


DEMO_EVENTS = [
    {
        "name": "Sunset Pool BBQ",
        "description": "Outdoor barbecue and sunset viewing party at the resort pool.",
        "location_name": "Outdoor Pool",
        "location_type": "OUTDOOR",
        "latitude": 8.8935,
        "longitude": 76.6145,
        "start_time_hour": 16,
        "end_time_hour": 19,
        "expected_guests": 60,
        "capacity": 80,
        "weather_dependent": True,
        "indoor_alternative": "Palm Ballroom",
        "indoor_alt_latitude": 8.8930,
        "indoor_alt_longitude": 76.6140,
        "indoor_alt_capacity": 80,
        "status": "SCHEDULED",
        "is_demo": True,
    },
]


def seed_phase1_demo(db: Session, resort_id: int) -> dict:
    """
    Idempotently seed Phase 1 demo data for resort.
    Returns summary of seeded records.
    """
    from app.models.location import ResortLocation
    from app.models.resort_event import ResortEvent

    seeded = {"locations": 0, "events": 0, "skipped": 0}

    # ── Locations ─────────────────────────────────────────────────────────────
    existing_location_names = {
        loc.name
        for loc in db.query(ResortLocation)
                     .filter(ResortLocation.resort_id == resort_id)
                     .all()
    }

    for loc_data in DEMO_LOCATIONS:
        if loc_data["name"] in existing_location_names:
            seeded["skipped"] += 1
            continue
        loc = ResortLocation(
            resort_id=resort_id,
            name=loc_data["name"],
            location_type=loc_data["location_type"],
            indoor=loc_data["indoor"],
            is_outdoor=not loc_data["indoor"],
            is_weather_dependent=not loc_data["indoor"],
            latitude=loc_data["latitude"],
            longitude=loc_data["longitude"],
            capacity=loc_data["capacity"],
            description=loc_data["description"],
            is_demo_coordinates=True,
            active=True,
        )

        db.add(loc)
        seeded["locations"] += 1

    # ── Events ─────────────────────────────────────────────────────────────────
    existing_event_names = {
        ev.name
        for ev in db.query(ResortEvent)
                    .filter(
                        ResortEvent.resort_id == resort_id,
                        ResortEvent.is_demo.is_(True),
                    )
                    .all()
    }

    for ev_data in DEMO_EVENTS:
        if ev_data["name"] in existing_event_names:
            seeded["skipped"] += 1
            continue
        event = ResortEvent(
            resort_id=resort_id,
            name=ev_data["name"],
            description=ev_data["description"],
            location_name=ev_data["location_name"],
            location_type=ev_data["location_type"],
            latitude=ev_data["latitude"],
            longitude=ev_data["longitude"],
            start_time=_today_event_time(ev_data["start_time_hour"]),
            end_time=_today_event_time(ev_data["end_time_hour"]),
            expected_guests=ev_data["expected_guests"],
            capacity=ev_data["capacity"],
            weather_dependent=ev_data["weather_dependent"],
            indoor_alternative=ev_data["indoor_alternative"],
            indoor_alt_latitude=ev_data["indoor_alt_latitude"],
            indoor_alt_longitude=ev_data["indoor_alt_longitude"],
            indoor_alt_capacity=ev_data["indoor_alt_capacity"],
            status=ev_data["status"],
            is_demo=True,
        )
        db.add(event)
        seeded["events"] += 1

    db.commit()
    return seeded
