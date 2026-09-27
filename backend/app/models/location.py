"""
ResortLocation model – geospatial locations for Phase 1 map visualization.
Represents pools, ballrooms, restaurants, and other operational hotspots.
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base


class ResortLocation(Base):
    __tablename__ = "resort_locations"

    id = Column(Integer, primary_key=True, index=True)
    resort_id = Column(Integer, ForeignKey("resorts.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)               # "Outdoor Pool", "Palm Ballroom"
    location_type = Column(String(50), nullable=False)       # POOL | BALLROOM | RESTAURANT | GARDEN | RECEPTION | LOBBY | OTHER
    indoor = Column(Boolean, default=False)                  # True = indoor venue
    is_outdoor = Column(Boolean, default=False)              # Compatibility with table constraint
    is_weather_dependent = Column(Boolean, default=False)

    latitude = Column(Float, nullable=True)                  # Demo coords clearly marked
    longitude = Column(Float, nullable=True)

    capacity = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)

    # Demo data flag so we never claim fabricated coords are real
    is_demo_coordinates = Column(Boolean, default=True)


    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    resort = relationship("Resort", back_populates="resort_locations")
