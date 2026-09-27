from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
import os

from app.database.connection import Base, engine
from app.routes import (
    auth,
    dashboard,
    forecast,
    recommendations,
    tasks,
    inventory,
    guest_requests,
    activity_log,
    demo,
    front_desk,
    departments,
    guest_intelligence,
    weather,
    digital_twin,
)

# Load environment variables
load_dotenv()
APP_ENV = os.getenv("APP_ENV", "development").strip().casefold()
CORS_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]
if APP_ENV == "production":
    if not CORS_ORIGINS or "*" in CORS_ORIGINS:
        raise RuntimeError("CORS_ORIGINS must list the exact production frontend origin(s)")
else:
    CORS_ORIGINS = CORS_ORIGINS or ["http://localhost:3000", "http://localhost:5173"]

# Create FastAPI app
app = FastAPI(
    title="Smart Resort 360 API",
    description="AI-powered resort operations and decision-support platform",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.on_event("startup")
def create_additive_tables():
    """Create newly introduced tables without altering existing V1/V2 tables."""
    # Phase 1: ensure new models are imported so SQLAlchemy registers them
    from app.models.resort_event import ResortEvent     # noqa: F401
    from app.models.location import ResortLocation      # noqa: F401
    from app.models.weather_cache import WeatherCache   # noqa: F401
    Base.metadata.create_all(bind=engine)
    training_flag_tables = (
        "guest_profiles",
        "resort_activities",
        "guest_activity_interactions",
        "guest_feedback",
        "guest_requests",
    )
    with engine.begin() as connection:
        inspector = inspect(connection)
        for table_name in training_flag_tables:
            if table_name in inspector.get_table_names():
                columns = {column["name"] for column in inspector.get_columns(table_name)}
                if "is_training_sample" not in columns:
                    connection.execute(text(
                        f"ALTER TABLE {table_name} ADD COLUMN is_training_sample BOOLEAN NOT NULL DEFAULT FALSE"
                    ))
        
        # Check resorts table for latitude and longitude
        if "resorts" in inspector.get_table_names():
            resort_columns = {column["name"] for column in inspector.get_columns("resorts")}
            if "latitude" not in resort_columns:
                connection.execute(text("ALTER TABLE resorts ADD COLUMN latitude FLOAT DEFAULT 15.2993"))
            if "longitude" not in resort_columns:
                connection.execute(text("ALTER TABLE resorts ADD COLUMN longitude FLOAT DEFAULT 73.9876"))

        # Check resort_locations table columns
        if "resort_locations" in inspector.get_table_names():
            loc_columns = {column["name"] for column in inspector.get_columns("resort_locations")}
            if "indoor" not in loc_columns:
                connection.execute(text("ALTER TABLE resort_locations ADD COLUMN indoor BOOLEAN DEFAULT FALSE"))
            if "is_demo_coordinates" not in loc_columns:
                connection.execute(text("ALTER TABLE resort_locations ADD COLUMN is_demo_coordinates BOOLEAN DEFAULT TRUE"))
            if "active" not in loc_columns:
                connection.execute(text("ALTER TABLE resort_locations ADD COLUMN active BOOLEAN DEFAULT TRUE"))



# CORS middleware - Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(forecast.router)
app.include_router(recommendations.router)
app.include_router(tasks.router)
app.include_router(inventory.router)
app.include_router(guest_requests.router)
app.include_router(activity_log.router)
app.include_router(demo.router)
app.include_router(front_desk.router)
app.include_router(departments.router)
app.include_router(guest_intelligence.router)
# Phase 1: Real-time weather + Digital Twin
app.include_router(weather.router)
app.include_router(digital_twin.router)


@app.get("/")
def root():
    """API root endpoint with system information"""
    return {
        "service": "Smart Resort 360 API",
        "version": "2.0.0",
        "status": "operational",
        "description": "AI-powered resort operations orchestration platform",
        "docs": "/docs",
        "features": [
            "ML-based occupancy forecasting",
            "Predictive staffing recommendations",
            "Inventory stockout prediction",
            "Explainable AI recommendations",
            "Closed-loop decision workflow",
            "Multi-role operational dashboards",
            "Guest request management",
            "Activity audit logging",
            "Real-time weather integration (Phase 1)",
            "Resort Digital Twin simulation (Phase 1)",
            "Weather impact propagation (Phase 1)",
            "Geospatial resort visualization (Phase 1)",
        ]
    }


@app.get("/health")
def health_check():
    """Health check endpoint for deployment monitoring."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "database": "disconnected", "version": app.version},
        )
    return {
        "status": "ok",
        "database": "connected",
        "version": app.version,
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
