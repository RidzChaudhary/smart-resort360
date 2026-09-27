"""
Data Fusion Engine - Creates unified OperationalSnapshot.
Combines resort operational data with real-time weather for AI analysis.

Phase 1 Enhancement: now includes ResortEvent (dedicated event model)
alongside the existing ResortActivity support.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models import (
    Resort, Room, Booking, Department, User, Task,
    GuestRequest, InventoryItem, ResortActivity
)
from app.services.weather_service import WeatherUnavailableError, get_weather_service


class DataFusionEngine:
    """
    Fuses internal resort telemetry with external signals (weather)
    into a unified OperationalSnapshot for AI/Digital Twin consumption.
    """

    def __init__(self, db: Session, resort_id: int):
        self.db = db
        self.resort_id = resort_id
        self.weather_service = get_weather_service()

    def _get_resort_state(self) -> Dict[str, Any]:
        """Get current resort operational state."""
        resort = self.db.query(Resort).filter(Resort.id == self.resort_id).first()
        if not resort:
            raise ValueError(f"Resort {self.resort_id} not found")

        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Room status breakdown
        total_rooms = resort.total_rooms

        # Count rooms by status
        room_statuses = self.db.query(
            Room.status, func.count(Room.id)
        ).filter(Room.resort_id == self.resort_id).group_by(Room.status).all()

        status_counts = {status: count for status, count in room_statuses}

        # Calculate occupancy
        occupied_rooms = status_counts.get("occupied", 0)
        maintenance_rooms = status_counts.get("maintenance", 0) + status_counts.get("out_of_service", 0)
        sellable_rooms = total_rooms - maintenance_rooms

        occupancy_pct = (occupied_rooms / sellable_rooms * 100) if sellable_rooms > 0 else 0

        # Today's check-ins and check-outs
        todays_check_ins = self.db.query(func.count(Booking.id)).filter(
            and_(
                Booking.resort_id == self.resort_id,
                func.date(Booking.check_in) == today.date(),
                Booking.status.in_(["confirmed", "checked_in"])
            )
        ).scalar() or 0

        todays_check_outs = self.db.query(func.count(Booking.id)).filter(
            and_(
                Booking.resort_id == self.resort_id,
                func.date(Booking.check_out) == today.date(),
                Booking.status.in_(["confirmed", "checked_in"])
            )
        ).scalar() or 0

        # Early arrivals
        early_arrivals = self.db.query(func.count(Booking.id)).filter(
            and_(
                Booking.resort_id == self.resort_id,
                func.date(Booking.check_in) == today.date(),
                Booking.early_arrival == True,
                Booking.status == "confirmed"
            )
        ).scalar() or 0

        return {
            "total_rooms": total_rooms,
            "occupied_rooms": occupied_rooms,
            "occupancy_pct": round(occupancy_pct, 1),
            "sellable_rooms": sellable_rooms,
            "todays_check_ins": todays_check_ins,
            "todays_check_outs": todays_check_outs,
            "early_arrivals": early_arrivals,
            "rooms_clean": status_counts.get("clean", 0),
            "rooms_dirty": status_counts.get("dirty", 0),
            "rooms_inspecting": status_counts.get("inspecting", 0),
            "rooms_maintenance": maintenance_rooms,
            "room_status_breakdown": status_counts
        }

    def _get_staff_availability(self) -> Dict[str, Any]:
        """Get staff availability by department."""
        departments = self.db.query(Department).filter(
            Department.resort_id == self.resort_id
        ).all()

        staff_by_dept = {}

        for dept in departments:
            # Count scheduled staff
            total_staff = self.db.query(func.count(User.id)).filter(
                and_(
                    User.resort_id == self.resort_id,
                    User.department_id == dept.id,
                    User.role.in_(["STAFF", "DEPARTMENT_HEAD"])
                )
            ).scalar() or 0

            # Count busy staff (those with in-progress tasks)
            busy_staff = self.db.query(func.count(func.distinct(Task.assigned_to))).filter(
                and_(
                    Task.resort_id == self.resort_id,
                    Task.department_id == dept.id,
                    Task.status.in_(["IN_PROGRESS", "ASSIGNED"]),
                    Task.assigned_to.isnot(None)
                )
            ).scalar() or 0

            available_staff = max(total_staff - busy_staff, 0)

            staff_by_dept[dept.name] = {
                "scheduled": total_staff,
                "busy": busy_staff,
                "available": available_staff
            }

        return staff_by_dept

    def _get_events(self) -> List[Dict[str, Any]]:
        """
        Get today's and upcoming events.
        Checks ResortEvent table first (Phase 1), then falls back to ResortActivity.
        """
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        event_list = []

        # ── Phase 1: ResortEvent (dedicated event model with geospatial data) ──
        try:
            from app.models.resort_event import ResortEvent
            resort_events = self.db.query(ResortEvent).filter(
                and_(
                    ResortEvent.resort_id == self.resort_id,
                    ResortEvent.start_time >= today,
                    ResortEvent.start_time < tomorrow + timedelta(days=1),
                    ResortEvent.status != "CANCELLED",
                )
            ).all()

            for ev in resort_events:
                event_list.append({
                    "id": ev.id,
                    "source": "resort_event",
                    "name": ev.name,
                    "description": ev.description,
                    "location_name": ev.location_name,
                    "location_type": ev.location_type,          # "OUTDOOR" | "INDOOR"
                    "latitude": ev.latitude,
                    "longitude": ev.longitude,
                    "start_at": ev.start_time.isoformat() if ev.start_time else None,
                    "end_at": ev.end_time.isoformat() if ev.end_time else None,
                    "capacity": ev.capacity,
                    "expected_guests": ev.expected_guests,
                    "weather_dependent": ev.weather_dependent,
                    "outdoor": ev.location_type == "OUTDOOR",   # normalised bool
                    "indoor_alternative": ev.indoor_alternative,
                    "indoor_alt_latitude": ev.indoor_alt_latitude,
                    "indoor_alt_longitude": ev.indoor_alt_longitude,
                    "indoor_alt_capacity": ev.indoor_alt_capacity,
                    "status": ev.status,
                })
        except Exception:
            pass  # Table may not exist yet on first boot – startup creates it

        # ── Legacy: ResortActivity events (weather keywords heuristic) ──
        activities = self.db.query(ResortActivity).filter(
            and_(
                ResortActivity.resort_id == self.resort_id,
                ResortActivity.active == True,
                ResortActivity.start_at >= today,
                ResortActivity.start_at < tomorrow + timedelta(days=1)
            )
        ).all()

        for event in activities:
            is_outdoor = any(
                keyword in event.name.lower() or keyword in event.category.lower()
                for keyword in ["pool", "beach", "outdoor", "garden", "patio", "terrace"]
            )
            weather_dependent = is_outdoor or any(
                keyword in event.name.lower()
                for keyword in ["sunset", "bbq", "grill", "picnic", "sports", "golf"]
            )
            event_list.append({
                "id": f"activity_{event.id}",
                "source": "resort_activity",
                "name": event.name,
                "category": event.category,
                "description": event.description,
                "start_at": event.start_at.isoformat() if event.start_at else None,
                "end_at": event.end_at.isoformat() if event.end_at else None,
                "capacity": event.capacity,
                "available_slots": event.available_slots,
                "expected_guests": event.capacity - event.available_slots,
                "location_type": "OUTDOOR" if is_outdoor else "INDOOR",
                "outdoor": is_outdoor,
                "weather_dependent": weather_dependent,
                "crowd_level": event.crowd_level,
                "latitude": None,
                "longitude": None,
                "indoor_alternative": None,
                "indoor_alt_capacity": None,
            })

        return event_list

    def _get_operational_issues(self) -> Dict[str, Any]:
        """Get current operational issues and risks."""
        # Open guest requests
        open_requests_count = self.db.query(func.count(GuestRequest.id)).filter(
            and_(
                GuestRequest.resort_id == self.resort_id,
                GuestRequest.status.in_(["PENDING", "IN_PROGRESS"])
            )
        ).scalar() or 0

        # Get high-priority guest requests
        high_priority_requests = self.db.query(GuestRequest).filter(
            and_(
                GuestRequest.resort_id == self.resort_id,
                GuestRequest.status.in_(["PENDING", "IN_PROGRESS"]),
                GuestRequest.priority.in_(["HIGH", "CRITICAL"])
            )
        ).limit(10).all()

        # Task statistics
        open_tasks = self.db.query(Task).filter(
            and_(
                Task.resort_id == self.resort_id,
                Task.status.in_(["PENDING", "ASSIGNED", "IN_PROGRESS", "BLOCKED", "ESCALATED"])
            )
        ).all()

        overdue_tasks = [task for task in open_tasks if task.is_overdue]
        blocked_tasks = [task for task in open_tasks if task.status == "BLOCKED"]
        critical_tasks = [task for task in open_tasks if task.priority in ["HIGH", "CRITICAL"]]

        return {
            "open_guest_requests": open_requests_count,
            "high_priority_requests": [
                {
                    "id": req.id,
                    "room_number": req.room_number,
                    "type": req.request_type,
                    "priority": req.priority,
                    "description": req.description[:100]
                }
                for req in high_priority_requests
            ],
            "total_open_tasks": len(open_tasks),
            "overdue_tasks": len(overdue_tasks),
            "blocked_tasks": len(blocked_tasks),
            "critical_tasks": len(critical_tasks)
        }

    def _get_inventory_status(self) -> List[Dict[str, Any]]:
        """Get inventory items at risk."""
        items_at_risk = self.db.query(InventoryItem).filter(
            and_(
                InventoryItem.resort_id == self.resort_id,
                InventoryItem.current_stock <= InventoryItem.reorder_threshold
            )
        ).limit(10).all()

        return [
            {
                "id": item.id,
                "name": item.name,
                "category": item.category,
                "current_stock": item.current_stock,
                "reorder_threshold": item.reorder_threshold,
                "unit": item.unit
            }
            for item in items_at_risk
        ]

    def _get_weather_data(self) -> Dict[str, Any]:
        """Get current weather and forecast."""
        try:
            current = self.weather_service.get_current_weather(db=self.db, resort_id=self.resort_id)
            forecast = self.weather_service.get_hourly_forecast(24, db=self.db, resort_id=self.resort_id)
            risk_window = self.weather_service.get_high_risk_window(db=self.db, resort_id=self.resort_id)
        except WeatherUnavailableError:
            return {
                "available": False,
                "status": "unavailable",
                "message": "Live weather and recent cached weather are unavailable.",
                "current": None,
                "hourly_forecast": [],
                "high_risk_window": None,
            }

        return {
            "available": True,
            "status": "available",
            "current": current,
            "hourly_forecast": forecast,
            "high_risk_window": risk_window
        }

    def create_operational_snapshot(self) -> Dict[str, Any]:
        """
        Create unified OperationalSnapshot combining all resort data + weather.
        This is the single source of truth for AI/Digital Twin analysis.
        """
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "resort_id": self.resort_id,
            "resort_state": self._get_resort_state(),
            "staff_availability": self._get_staff_availability(),
            "events": self._get_events(),
            "operational_issues": self._get_operational_issues(),
            "inventory_at_risk": self._get_inventory_status(),
            "weather": self._get_weather_data()
        }

        return snapshot


def get_operational_snapshot(db: Session, resort_id: int) -> Dict[str, Any]:
    """Convenience function to get operational snapshot."""
    fusion_engine = DataFusionEngine(db, resort_id)
    return fusion_engine.create_operational_snapshot()
