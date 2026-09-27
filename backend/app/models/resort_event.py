"""
ResortEvent model – minimal event entity for Phase 1.
Does NOT modify existing models. Appended to Base, auto-created on startup.
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base


class ResortEvent(Base):
    __tablename__ = "resort_events"

    id = Column(Integer, primary_key=True, index=True)
    resort_id = Column(Integer, ForeignKey("resorts.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Location info
    location_name = Column(String(255), nullable=False)          # e.g. "Outdoor Pool"
    location_type = Column(String(50), default="OUTDOOR")        # OUTDOOR | INDOOR
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Timing
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    # Capacity / guests
    expected_guests = Column(Integer, default=0)
    capacity = Column(Integer, default=0)

    # Weather sensitivity
    weather_dependent = Column(Boolean, default=True)
    indoor_alternative = Column(String(255), nullable=True)      # e.g. "Palm Ballroom"
    indoor_alt_latitude = Column(Float, nullable=True)
    indoor_alt_longitude = Column(Float, nullable=True)
    indoor_alt_capacity = Column(Integer, nullable=True)

    # Status
    status = Column(String(50), default="SCHEDULED")             # SCHEDULED | ACTIVE | CANCELLED | MOVED_INDOOR
    is_demo = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    resort = relationship("Resort", back_populates="resort_events")
