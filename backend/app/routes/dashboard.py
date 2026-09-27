from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from typing import Dict, Any

from app.database.connection import get_db
from app.models import User, Recommendation, Task, Room, Booking, ActivityLog, Department, GuestRequest, InventoryItem
from app.services.forecast_engine import ForecastEngine
from app.utils.auth import get_current_user, require_role, require_department_head, get_department_head_department_id
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/dashboard", tags=["Dashboards"])

@router.get("/manager")
def get_manager_dashboard(
    current_user: User = Depends(require_role(["MANAGER"])),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Manager dashboard with KPIs, pending recommendations, and system health.
    """
    resort_id = current_user.resort_id

    # KPIs
    capacity = ForecastEngine(db, resort_id).get_room_capacity()
    total_rooms = capacity["total_rooms"]
    sellable_rooms = capacity["sellable_rooms"]

    # Today's occupancy
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_occupied = db.query(func.count(func.distinct(Booking.room_id))).filter(
        and_(
            Booking.resort_id == resort_id,
            Booking.check_in <= today,
            Booking.check_out > today,
            Booking.status.in_(["confirmed", "checked_in"])
        )
    ).scalar() or 0

    occupancy_pct = min((today_occupied / sellable_rooms * 100), 100) if sellable_rooms > 0 else 0

    booking_demand = db.query(func.count(Booking.id)).filter(
        and_(
            Booking.resort_id == resort_id,
            Booking.check_in <= today,
            Booking.check_out > today,
            Booking.status.in_(["confirmed", "checked_in"])
        )
    ).scalar() or 0

    # Tomorrow's check-ins
    tomorrow = today + timedelta(days=1)
    tomorrow_check_ins = db.query(func.count(Booking.id)).filter(
        and_(
            Booking.resort_id == resort_id,
            func.date(Booking.check_in) == tomorrow.date(),
            Booking.status.in_(["confirmed", "checked_in"])
        )
    ).scalar() or 0

    # Pending recommendations
    pending_recommendations = db.query(Recommendation).filter(
        and_(
            Recommendation.resort_id == resort_id,
            Recommendation.status == "PENDING"
        )
    ).order_by(Recommendation.priority.desc(), Recommendation.created_at.desc()).all()

    # Critical tasks
    critical_tasks = db.query(Task).filter(
        and_(
            Task.resort_id == resort_id,
            Task.priority.in_(["HIGH", "CRITICAL"]),
            Task.status.in_(["PENDING", "ASSIGNED", "IN_PROGRESS", "BLOCKED", "ESCALATED"])
        )
    ).count()

    open_tasks = db.query(Task).filter(
        and_(Task.resort_id == resort_id, Task.status.notin_(["COMPLETED", "CANCELLED"]))
    ).all()
    open_guest_issues = db.query(GuestRequest).filter(
        and_(
            GuestRequest.resort_id == resort_id,
            GuestRequest.status.in_(["PENDING", "IN_PROGRESS"]),
            GuestRequest.is_training_sample.is_(False),
        )
    ).count()
    inventory_risks = db.query(InventoryItem).filter(
        and_(InventoryItem.resort_id == resort_id, InventoryItem.current_stock <= InventoryItem.reorder_threshold)
    ).count()

    def serialize_task(task):
        return {
            "id": task.id,
            "title": task.title,
            "room_number": task.room_number,
            "priority": task.priority,
            "status": task.status,
            "department": task.department.name if task.department else None,
            "assignee": task.assignee.name if task.assignee else "Unassigned",
            "minutes_overdue": task.minutes_overdue,
            "blocker_reason": task.blocker_reason,
        }

    attention_queues = {
        "overdue_tasks": [serialize_task(task) for task in open_tasks if task.is_overdue][:20],
        "blocked_tasks": [serialize_task(task) for task in open_tasks if task.status == "BLOCKED"][:20],
        "escalated_tasks": [serialize_task(task) for task in open_tasks if task.status == "ESCALATED"][:20],
        "critical_tasks": [serialize_task(task) for task in open_tasks if task.priority in {"HIGH", "CRITICAL"}][:20],
        "guest_issues": [
            {
                "id": issue.id,
                "room_number": issue.room_number,
                "request_type": issue.request_type,
                "description": issue.description,
                "priority": issue.priority,
                "status": issue.status,
            }
            for issue in db.query(GuestRequest).filter(
                GuestRequest.resort_id == resort_id,
                GuestRequest.status.in_(["PENDING", "IN_PROGRESS"]),
                GuestRequest.is_training_sample.is_(False),
            ).order_by(GuestRequest.created_at.desc()).limit(20).all()
        ],
        "inventory_risks": [
            {
                "id": item.id,
                "name": item.name,
                "current_stock": item.current_stock,
                "reorder_threshold": item.reorder_threshold,
                "unit": item.unit,
                "category": item.category,
                "department": (
                    "Food & Beverage" if item.category == "F&B"
                    else "Housekeeping" if item.category in {"Housekeeping", "Guest Amenities"}
                    else "Maintenance" if item.category == "Maintenance"
                    else item.category
                ),
            }
            for item in db.query(InventoryItem).filter(
                InventoryItem.resort_id == resort_id,
                InventoryItem.current_stock <= InventoryItem.reorder_threshold,
            ).order_by(InventoryItem.current_stock.asc()).limit(20).all()
        ],
    }

    # Recent activity logs
    recent_activity = db.query(ActivityLog).filter(
        ActivityLog.resort_id == resort_id
    ).order_by(desc(ActivityLog.created_at)).limit(10).all()

    # Room status breakdown
    room_status_breakdown = db.query(
        Room.status, func.count(Room.id)
    ).filter(Room.resort_id == resort_id).group_by(Room.status).all()

    return {
        "kpis": {
            "current_occupancy_pct": round(occupancy_pct, 1),
            "occupied_rooms": today_occupied,
            "total_rooms": total_rooms,
            "sellable_rooms": sellable_rooms,
            "booking_demand": booking_demand,
            "overbooking_count": max(booking_demand - sellable_rooms, 0),
            "tomorrow_check_ins": tomorrow_check_ins,
            "pending_recommendations": len(pending_recommendations),
            "critical_tasks": critical_tasks,
            "open_tasks": len(open_tasks),
            "overdue_tasks": sum(1 for task in open_tasks if task.is_overdue),
            "blocked_tasks": sum(1 for task in open_tasks if task.status == "BLOCKED"),
            "escalated_tasks": sum(1 for task in open_tasks if task.status == "ESCALATED"),
            "open_guest_issues": open_guest_issues,
            "inventory_risks": inventory_risks,
            "rooms_unavailable": capacity["unavailable_rooms"]
        },
        "pending_recommendations": [
            {
                "id": rec.id,
                "type": rec.type,
                "priority": rec.priority,
                "title": rec.title,
                "recommended_action": rec.recommended_action,
                "explanation": rec.explanation,
                "expected_impact": rec.expected_impact,
                "metrics_data": rec.metrics_data,
                "target_date": rec.target_date,
                "created_at": rec.created_at.isoformat()
            }
            for rec in pending_recommendations
        ],
        "room_status_breakdown": {status: count for status, count in room_status_breakdown},
        "attention_queues": attention_queues,
        "recent_activity": [
            {
                "id": log.id,
                "user_name": log.user_name,
                "user_role": log.user_role,
                "action_type": log.action_type,
                "description": log.description,
                "created_at": log.created_at.isoformat()
            }
            for log in recent_activity
        ]
    }


@router.get("/front-desk")
def get_front_desk_dashboard(
    current_user: User = Depends(require_role(["FRONT_DESK"])),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Front Desk dashboard with check-ins, check-outs, room readiness.
    """
    resort_id = current_user.resort_id
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Today's check-ins
    todays_check_ins = db.query(Booking).filter(
        and_(
            Booking.resort_id == resort_id,
            func.date(Booking.check_in) == today.date(),
            Booking.status.in_(["confirmed", "checked_in"])
        )
    ).all()

    # Today's check-outs
    todays_check_outs = db.query(Booking).filter(
        and_(
            Booking.resort_id == resort_id,
            func.date(Booking.check_out) == today.date(),
            Booking.status.in_(["confirmed", "checked_in"])
        )
    ).all()

    # Room readiness
    clean_rooms = db.query(func.count(Room.id)).filter(
        and_(Room.resort_id == resort_id, Room.status == "clean")
    ).scalar() or 0

    dirty_rooms = db.query(func.count(Room.id)).filter(
        and_(Room.resort_id == resort_id, Room.status == "dirty")
    ).scalar() or 0

    inspecting_rooms = db.query(func.count(Room.id)).filter(
        and_(Room.resort_id == resort_id, Room.status == "inspecting")
    ).scalar() or 0

    maintenance_rooms = db.query(func.count(Room.id)).filter(
        and_(Room.resort_id == resort_id, Room.status == "maintenance")
    ).scalar() or 0

    return {
        "todays_check_ins": [
            {
                "id": b.id,
                "room_number": b.room.room_number if b.room else "TBA",
                "guest_name": b.guest_name,
                "guests_count": b.guests_count,
                "early_arrival": b.early_arrival,
                "expected_arrival_time": b.expected_arrival_time,
                "status": b.status
            }
            for b in todays_check_ins
        ],
        "todays_check_outs": [
            {
                "id": b.id,
                "room_number": b.room.room_number if b.room else "TBA",
                "guest_name": b.guest_name,
                "status": b.status
            }
            for b in todays_check_outs
        ],
        "room_readiness": {
            "clean": clean_rooms,
            "dirty": dirty_rooms,
            "inspecting": inspecting_rooms,
            "maintenance": maintenance_rooms
        }
    }


@router.get("/department")
def get_department_dashboard(
    current_user: User = Depends(require_department_head),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Department Head dashboard with assigned tasks and team workload.
    """
    resort_id = current_user.resort_id
    department_id = get_department_head_department_id(current_user)

    # Get department info
    department = db.query(Department).filter(
        Department.id == department_id,
        Department.resort_id == resort_id,
    ).first()

    # Department tasks
    tasks = db.query(Task).filter(
        and_(
            Task.resort_id == resort_id,
            Task.department_id == department_id
        )
    ).order_by(Task.priority.desc(), Task.created_at.desc()).all()

    # Team members
    team_members = db.query(User).filter(
        and_(
            User.resort_id == resort_id,
            User.department_id == department_id,
            User.role == "STAFF"
        )
    ).all()

    # Task status breakdown
    pending_tasks = sum(1 for t in tasks if t.status == "PENDING")
    in_progress_tasks = sum(1 for t in tasks if t.status == "IN_PROGRESS")
    completed_tasks = sum(1 for t in tasks if t.status == "COMPLETED")

    return {
        "department": {
            "id": department.id,
            "name": department.name
        } if department else None,
        "task_summary": {
            "pending": pending_tasks,
            "in_progress": in_progress_tasks,
            "completed": completed_tasks,
            "assigned": sum(1 for t in tasks if t.status == "ASSIGNED"),
            "blocked": sum(1 for t in tasks if t.status == "BLOCKED"),
            "escalated": sum(1 for t in tasks if t.status == "ESCALATED"),
            "overdue": sum(1 for t in tasks if t.is_overdue),
            "total": len(tasks)
        },
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "priority": t.priority,
                "status": t.status,
                "assigned_to": t.assigned_to,
                "assignee_name": t.assignee.name if t.assignee else "Unassigned",
                "assignee_id": t.assigned_to,
                "room_number": t.room_number,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "sla_minutes": t.sla_minutes,
                "blocker_reason": t.blocker_reason,
                "escalated_to_user_id": t.escalated_to_user_id,
                "escalated_at": t.escalated_at.isoformat() if t.escalated_at else None,
                "is_overdue": t.is_overdue,
                "minutes_overdue": t.minutes_overdue,
                "created_at": t.created_at.isoformat()
            }
            for t in tasks
        ],
        "team_members": [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "phone": u.phone,
                "avatar_url": u.avatar_url
            }
            for u in team_members
        ]
    }


@router.get("/staff")
def get_staff_dashboard(
    current_user: User = Depends(require_role(["STAFF"])),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Staff dashboard with assigned tasks only.
    """
    resort_id = current_user.resort_id
    user_id = current_user.id

    # My assigned tasks
    my_tasks = db.query(Task).filter(
        and_(
            Task.resort_id == resort_id,
            Task.assigned_to == user_id
        )
    ).order_by(Task.priority.desc(), Task.due_date.asc()).all()

    return {
        "my_tasks": [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "priority": t.priority,
                "status": t.status,
                "room_number": t.room_number,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "sla_minutes": t.sla_minutes,
                "blocker_reason": t.blocker_reason,
                "escalated_to_user_id": t.escalated_to_user_id,
                "escalated_at": t.escalated_at.isoformat() if t.escalated_at else None,
                "is_overdue": t.is_overdue,
                "minutes_overdue": t.minutes_overdue,
                "created_at": t.created_at.isoformat()
            }
            for t in my_tasks
        ],
        "summary": {
            "pending": sum(1 for t in my_tasks if t.status == "PENDING"),
            "assigned": sum(1 for t in my_tasks if t.status == "ASSIGNED"),
            "in_progress": sum(1 for t in my_tasks if t.status == "IN_PROGRESS"),
            "blocked": sum(1 for t in my_tasks if t.status == "BLOCKED"),
            "escalated": sum(1 for t in my_tasks if t.status == "ESCALATED"),
            "overdue": sum(1 for t in my_tasks if t.is_overdue),
            "completed_today": sum(
                1 for t in my_tasks
                if t.status == "COMPLETED" and t.completed_at and t.completed_at.date() == datetime.utcnow().date()
            )
        }
    }
