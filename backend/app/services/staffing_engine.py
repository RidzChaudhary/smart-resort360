import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models import Booking, Room, User, Department

class StaffingEngine:
    """
    Predictive staffing engine for resort departments.
    Identifies workload spikes and staffing gaps, generating actionable recommendations.
    """

    def __init__(self, db: Session, resort_id: int):
        self.db = db
        self.resort_id = resort_id

    def analyze_housekeeping_needs(self, target_date: datetime) -> Dict[str, Any]:
        """
        Analyze housekeeping workload and staffing requirements for a target date.
        Formula:
          Rooms to clean = Check-outs + Dirty rooms + Early arrival priority
          Required housekeepers = ceil(Rooms to clean / Rooms per staff member [10])
          Staffing gap = Required - Scheduled
        """
        target_date_only = target_date.date()

        # Check-outs on target date
        check_outs = self.db.query(func.count(Booking.id)).filter(
            and_(
                Booking.resort_id == self.resort_id,
                func.date(Booking.check_out) == target_date_only,
                Booking.status.in_(["confirmed", "checked_in", "checked_out"])
            )
        ).scalar() or 0

        # Currently dirty rooms in the resort
        dirty_rooms = self.db.query(func.count(Room.id)).filter(
            and_(
                Room.resort_id == self.resort_id,
                Room.status.in_(["dirty", "inspecting"])
            )
        ).scalar() or 0

        # Early arrivals (need fast-track cleaning)
        early_arrivals = self.db.query(func.count(Booking.id)).filter(
            and_(
                Booking.resort_id == self.resort_id,
                func.date(Booking.check_in) == target_date_only,
                Booking.early_arrival == True,
                Booking.status.in_(["confirmed", "checked_in"])
            )
        ).scalar() or 0

        # Total check-ins for day
        total_check_ins = self.db.query(func.count(Booking.id)).filter(
            and_(
                Booking.resort_id == self.resort_id,
                func.date(Booking.check_in) == target_date_only,
                Booking.status.in_(["confirmed", "checked_in"])
            )
        ).scalar() or 0

        # Rooms requiring full turnaround cleaning
        # Baseline = check-outs + existing dirty + early arrivals requiring priority prep
        rooms_to_clean = check_outs + dirty_rooms + early_arrivals

        # Productivity standard: 10 rooms per housekeeper per 8-hour shift
        rooms_per_housekeeper = 10
        required_housekeepers = int(np.ceil(rooms_to_clean / rooms_per_housekeeper)) if rooms_to_clean > 0 else 0

        # Query scheduled/active housekeeping staff
        hk_department = self.db.query(Department).filter(
            and_(
                Department.resort_id == self.resort_id,
                Department.name.ilike("%housekeeping%")
            )
        ).first()

        hk_staff_count = 0
        if hk_department:
            hk_staff_count = self.db.query(func.count(User.id)).filter(
                and_(
                    User.resort_id == self.resort_id,
                    User.department_id == hk_department.id,
                    User.role == "STAFF"
                )
            ).scalar() or 0

        # Shift schedules are not modeled yet; use the actual department roster as capacity.
        scheduled_staff = hk_staff_count
        current_cleaning_capacity = scheduled_staff * rooms_per_housekeeper

        staffing_gap = required_housekeepers - scheduled_staff
        has_risk = staffing_gap > 0 or rooms_to_clean > current_cleaning_capacity

        priority = "CRITICAL" if staffing_gap >= 3 else ("HIGH" if staffing_gap >= 1 else "LOW")

        return {
            "target_date": target_date.strftime("%Y-%m-%d"),
            "department_name": "Housekeeping",
            "department_id": hk_department.id if hk_department else None,
            "check_outs": check_outs,
            "dirty_rooms": dirty_rooms,
            "early_arrivals": early_arrivals,
            "total_check_ins": total_check_ins,
            "rooms_to_clean": rooms_to_clean,
            "rooms_per_housekeeper": rooms_per_housekeeper,
            "required_housekeepers": required_housekeepers,
            "scheduled_staff": scheduled_staff,
            "current_capacity_rooms": current_cleaning_capacity,
            "staffing_gap": max(0, staffing_gap),
            "has_risk": has_risk,
            "priority": priority
        }

    def generate_housekeeping_recommendation(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate explainable recommendation for Housekeeping department.
        """
        gap = analysis["staffing_gap"]
        target_date_str = analysis["target_date"]

        explanation = (
            f"Expected workload: {analysis['rooms_to_clean']} rooms to clean "
            f"({analysis['check_outs']} check-outs, {analysis['dirty_rooms']} dirty rooms, "
            f"{analysis['early_arrivals']} early arrivals).\n"
            f"Current scheduled capacity: {analysis['current_capacity_rooms']} rooms "
            f"({analysis['scheduled_staff']} staff members × 10 rooms/staff).\n"
            f"Required staff: {analysis['required_housekeepers']} housekeepers."
        )

        expected_impact = (
            f"Ensures all {analysis['total_check_ins']} arriving guests receive ready rooms on time, "
            f"eliminating check-in delays and preventing early-arrival complaints."
        )

        return {
            "type": "staffing",
            "priority": analysis["priority"],
            "title": f"Add {gap} Housekeeper{'s' if gap > 1 else ''} for {target_date_str}",
            "recommended_action": f"Schedule {gap} additional housekeeping shift{'s' if gap > 1 else ''} on {target_date_str}.",
            "explanation": explanation,
            "expected_impact": expected_impact,
            "metrics_data": {
                "department": "Housekeeping",
                "department_id": analysis["department_id"],
                "target_date": target_date_str,
                "staff_needed": gap,
                "rooms_to_clean": analysis["rooms_to_clean"],
                "scheduled_staff": analysis["scheduled_staff"],
                "required_staff": analysis["required_housekeepers"],
                "current_capacity": analysis["current_capacity_rooms"]
            },
            "target_date": target_date_str,
            "status": "PENDING"
        }
