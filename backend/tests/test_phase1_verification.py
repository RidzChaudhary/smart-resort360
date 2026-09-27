"""
Verification Script for Phase 1:
Live Weather + Digital Twin + Geospatial Impact Foundation
"""
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.connection import SessionLocal, Base, engine
from app.models import Resort, Room, Booking, Department, User
from app.models.resort_event import ResortEvent
from app.models.location import ResortLocation
from app.models.weather_cache import WeatherCache
from app.services.weather_service import get_weather_service
from app.services.data_fusion import get_operational_snapshot
from app.services.digital_twin import create_digital_twin
from app.services.impact_propagation import analyze_weather_impact
from app.services.phase1_demo_seed import seed_phase1_demo

def test_phase1():
    print("=== STARTING PHASE 1 VERIFICATION ===")
    
    # 1. Create tables
    print("\n1. Verifying Database Tables...")
    from sqlalchemy import inspect, text
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "resorts" in inspector.get_table_names():
            resort_columns = {column["name"] for column in inspector.get_columns("resorts")}
            if "latitude" not in resort_columns:
                connection.execute(text("ALTER TABLE resorts ADD COLUMN latitude FLOAT DEFAULT 33.7701"))
            if "longitude" not in resort_columns:
                connection.execute(text("ALTER TABLE resorts ADD COLUMN longitude FLOAT DEFAULT -118.1937"))
        if "resort_locations" in inspector.get_table_names():
            loc_columns = {column["name"] for column in inspector.get_columns("resort_locations")}
            if "indoor" not in loc_columns:
                connection.execute(text("ALTER TABLE resort_locations ADD COLUMN indoor BOOLEAN DEFAULT FALSE"))
            if "is_demo_coordinates" not in loc_columns:
                connection.execute(text("ALTER TABLE resort_locations ADD COLUMN is_demo_coordinates BOOLEAN DEFAULT TRUE"))
            if "active" not in loc_columns:
                connection.execute(text("ALTER TABLE resort_locations ADD COLUMN active BOOLEAN DEFAULT TRUE"))

    print("[OK] Tables created/verified successfully.")

    
    db = SessionLocal()
    try:
        # Check default resort
        resort = db.query(Resort).first()
        if not resort:
            print("No resort found, creating demo resort...")
            resort = Resort(name="Azure Haven Resort", location="Coastal Bay, CA", total_rooms=100)
            db.add(resort)
            db.commit()
            db.refresh(resort)
        print(f"[OK] Using Resort: ID={resort.id}, Name='{resort.name}', Total Rooms={resort.total_rooms}")
        
        # 2. Seed Phase 1 demo data
        print("\n2. Testing Phase 1 Demo Data Seeding...")
        seed_result = seed_phase1_demo(db, resort.id)
        print(f"[OK] Seed Result: {seed_result}")
        
        locations_count = db.query(ResortLocation).filter(ResortLocation.resort_id == resort.id).count()
        events_count = db.query(ResortEvent).filter(ResortEvent.resort_id == resort.id).count()
        print(f"[OK] Locations in DB: {locations_count}, Events in DB: {events_count}")
        assert locations_count > 0, "Locations should be seeded"
        assert events_count > 0, "Events should be seeded"
        
        # 3. Test Weather Service
        print("\n3. Testing Weather Service (Open-Meteo & Cache)...")
        ws = get_weather_service()
        current_weather = ws.get_current_weather()
        print(f"[OK] Current Weather: Temp={current_weather['temperature_c']}C, Condition='{current_weather['condition']}', RainProb={current_weather['rain_probability']}%, Wind={current_weather['wind_speed_kmh']} km/h")
        
        forecast = ws.get_hourly_forecast(12)
        print(f"[OK] 12-Hour Forecast count: {len(forecast)}")
        assert len(forecast) == 12, "Should return 12 forecast items"
        
        # 4. Test Data Fusion (OperationalSnapshot)
        print("\n4. Testing Data Fusion Engine (OperationalSnapshot)...")
        snapshot = get_operational_snapshot(db, resort.id)
        print(f"[OK] Snapshot Generated: Timestamp={snapshot['timestamp']}")
        print(f"  - Occupancy: {snapshot['resort_state']['occupancy_pct']}% ({snapshot['resort_state']['occupied_rooms']}/{snapshot['resort_state']['total_rooms']} rooms)")
        print(f"  - Staff Departments: {list(snapshot['staff_availability'].keys())}")
        print(f"  - Events Count: {len(snapshot['events'])}")
        assert "weather" in snapshot, "Snapshot must contain weather telemetry"
        assert "resort_state" in snapshot, "Snapshot must contain resort_state"
        
        # 5. Test Digital Twin
        print("\n5. Testing Digital Twin (Immutable virtual state & What-If simulation)...")
        twin = create_digital_twin(db, resort.id)
        state = twin.get_current_state()
        print(f"[OK] Current State retrieved: {state.resort_id} @ {state.timestamp}")
        
        # Run severe storm simulation
        sim_state = twin.simulate_weather_change(
            rain_probability=85.0,
            rain_intensity_mm=10.0,
            wind_speed_kmh=42.0,
            duration_hours=4
        )
        print(f"[OK] Simulation run: Sim RainProb={sim_state['weather']['current']['rain_probability']}%, is_sim={sim_state.get('_is_simulation')}")
        assert sim_state.get("_is_simulation") is True, "Must be tagged as simulation"
        
        # Verify production DB is completely untouched by simulation
        recheck_snapshot = get_operational_snapshot(db, resort.id)
        assert recheck_snapshot["weather"]["current"]["rain_probability"] == current_weather["rain_probability"], "Production state must remain unmodified"
        print("[OK] Production state verified UNMODIFIED by simulation.")
        
        # 6. Test Impact Propagation Engine
        print("\n6. Testing Impact Propagation Engine...")
        impact = analyze_weather_impact(sim_state)
        print(f"[OK] Impact Analysis on Storm Scenario:")
        print(f"  - Risk Level: {impact['risk_level']} (Score: {impact['risk_score']})")
        print(f"  - Affected Events: {impact['affected_events_count']}")
        print(f"  - Affected Guests: {impact['affected_guests']}")
        print(f"  - Affected Departments: {impact['affected_departments']}")
        print(f"  - Alternative Venues: {impact['alternative_venues']}")
        print(f"  - Explanation: {impact['explanation']}")
        
        assert impact["affected_events_count"] > 0, "Outdoor event must be flagged in 85% rain simulation"
        assert len(impact["alternative_venues"]) > 0, "Alternative indoor venue must be suggested"
        
        print("\n=== ALL PHASE 1 TESTS PASSED SUCCESSFULLY! ===")
        
    finally:
        db.close()

if __name__ == "__main__":
    test_phase1()
