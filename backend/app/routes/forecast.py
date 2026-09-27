from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime, timedelta

from app.database.connection import get_db
from app.models import Department, InventoryItem, Room, Task, User
from app.utils.auth import get_current_user, get_department_head_department_id, require_department_head
from app.services.forecast_engine import ForecastEngine
from app.schemas import ForecastOverviewResponse

router = APIRouter(prefix="/api/forecast", tags=["Forecasting"])

@router.get("/occupancy", response_model=ForecastOverviewResponse)
def get_occupancy_forecast(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get 7-day occupancy forecast with ML predictions.

    Uses Linear Regression trained on historical booking patterns.
    Combines confirmed bookings with predictive modeling.

    Returns:
    - Daily occupancy predictions
    - Check-in/check-out forecasts
    - Housekeeping workload projections
    - Staffing requirements
    - Revenue estimates
    - ML confidence scores
    """
    resort_id = current_user.resort_id

    forecast_engine = ForecastEngine(db, resort_id)
    forecast_result = forecast_engine.generate_forecast(days)

    return forecast_result


@router.get("/workload")
def get_workload_forecast(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get departmental workload forecast derived from occupancy predictions.

    Returns workload metrics for:
    - Housekeeping (rooms to clean, turnovers)
    - Front Desk (check-ins/check-outs)
    - F&B (guest count, meal forecasts)
    """
    resort_id = current_user.resort_id

    forecast_engine = ForecastEngine(db, resort_id)
    forecast_result = forecast_engine.generate_forecast(days)
    forecast_days = forecast_result.get("forecast_days", [])

    # Extract workload-specific metrics
    workload_by_department = {
        "housekeeping": [
            {
                "date": day["date"],
                "day_name": day["day_name"],
                "rooms_to_clean": day["cleaning_workload_rooms"],
                "housekeepers_needed": day["housekeepers_needed"],
                "housekeepers_scheduled": day["housekeepers_scheduled"],
                "staffing_gap": day["staffing_gap"],
                "check_outs": day["check_outs"],
                "early_arrivals": day["early_arrivals"]
            }
            for day in forecast_days
        ],
        "front_desk": [
            {
                "date": day["date"],
                "day_name": day["day_name"],
                "check_ins": day["check_ins"],
                "check_outs": day["check_outs"],
                "early_arrivals": day["early_arrivals"],
                "occupancy_pct": day["predicted_occupancy_pct"]
            }
            for day in forecast_days
        ],
        "food_beverage": [
            {
                "date": day["date"],
                "day_name": day["day_name"],
                "occupied_rooms": day["occupied_rooms"],
                "estimated_breakfast_guests": int(day["occupied_rooms"] * 1.8),  # avg 1.8 guests per room
                "estimated_dinner_covers": int(day["occupied_rooms"] * 1.3)  # ~60% dine at resort
            }
            for day in forecast_days
        ]
    }

    return {
        "workload_by_department": workload_by_department,
        "overall_summary": forecast_result.get("overall_summary", {}),
        "model_metadata": forecast_result.get("model_metadata", {})
    }


@router.get("/department")
def get_department_forecast(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(require_department_head),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    department_id = get_department_head_department_id(current_user)
    department = db.query(Department).filter(
        Department.id == department_id,
        Department.resort_id == current_user.resort_id,
    ).first()
    if department is None:
        raise HTTPException(status_code=404, detail="Department not found")

    department_name = department.name
    occupancy_forecast = ForecastEngine(db, current_user.resort_id).generate_forecast(days)
    occupancy_days = occupancy_forecast.get("forecast_days", [])
    columns = []
    summary_cards = []
    method_note = ""
    forecast_days = []

    if department_name == "Housekeeping":
        columns = [
            {"key": "predicted_occupancy_pct", "label": "Occupancy"},
            {"key": "check_outs", "label": "Check-outs"},
            {"key": "early_arrivals", "label": "Early arrivals"},
            {"key": "cleaning_workload_rooms", "label": "Rooms to prepare"},
            {"key": "housekeepers_needed", "label": "Staff needed"},
            {"key": "staffing_gap", "label": "Staff gap"},
        ]
        forecast_days = [{
            "date": day["date"],
            "day_name": day["day_name"],
            "metrics": {column["key"]: day[column["key"]] for column in columns},
        } for day in occupancy_days]
        summary_cards = [
            {"label": f"Rooms to prepare · {days} days", "value": sum(day["cleaning_workload_rooms"] for day in occupancy_days)},
            {"label": "Peak daily staffing gap", "value": max((day["staffing_gap"] for day in occupancy_days), default=0)},
            {"label": "Expected check-outs", "value": sum(day["check_outs"] for day in occupancy_days)},
        ]
        method_note = "Turnover and staffing estimates are derived from the resort occupancy forecast and recorded bookings."

    elif department_name == "Food & Beverage":
        columns = [
            {"key": "predicted_occupancy_pct", "label": "Occupancy"},
            {"key": "occupied_rooms", "label": "Occupied rooms"},
            {"key": "estimated_breakfast_guests", "label": "Breakfast covers · est."},
            {"key": "estimated_dinner_covers", "label": "Dinner covers · est."},
            {"key": "check_ins", "label": "Arrivals"},
        ]
        forecast_days = [{
            "date": day["date"],
            "day_name": day["day_name"],
            "metrics": {
                "predicted_occupancy_pct": day["predicted_occupancy_pct"],
                "occupied_rooms": day["occupied_rooms"],
                "estimated_breakfast_guests": round(day["occupied_rooms"] * 1.8),
                "estimated_dinner_covers": round(day["occupied_rooms"] * 1.3),
                "check_ins": day["check_ins"],
            },
        } for day in occupancy_days]
        summary_cards = [
            {"label": f"Breakfast covers · est. {days} days", "value": sum(day["metrics"]["estimated_breakfast_guests"] for day in forecast_days)},
            {"label": f"Dinner covers · est. {days} days", "value": sum(day["metrics"]["estimated_dinner_covers"] for day in forecast_days)},
            {"label": "Peak occupancy", "value": f"{max((day['predicted_occupancy_pct'] for day in occupancy_days), default=0)}%"},
        ]
        method_note = "Cover estimates use projected occupied rooms and planning averages of 1.8 breakfast guests and 1.3 dinner covers per room; they are estimates, not reservations."

    elif department_name == "Maintenance":
        open_tasks = db.query(Task).filter(
            Task.resort_id == current_user.resort_id,
            Task.department_id == department_id,
            Task.status.notin_(["COMPLETED", "CANCELLED"]),
        ).all()
        affected_rooms = db.query(Room).filter(
            Room.resort_id == current_user.resort_id,
            Room.status.in_(["maintenance", "repair", "out_of_service"]),
        ).count()
        columns = [
            {"key": "open_backlog", "label": "Open task backlog"},
            {"key": "tasks_due", "label": "Tasks due"},
            {"key": "blocked_tasks", "label": "Blocked tasks"},
            {"key": "overdue_tasks", "label": "Overdue by day-end"},
            {"key": "rooms_needing_service", "label": "Rooms needing service"},
        ]
        for day in occupancy_days:
            day_end = datetime.strptime(day["date"], "%Y-%m-%d") + timedelta(days=1)
            due_tasks = [task for task in open_tasks if task.due_date and task.due_date.date().isoformat() == day["date"]]
            forecast_days.append({
                "date": day["date"],
                "day_name": day["day_name"],
                "metrics": {
                    "open_backlog": len(open_tasks),
                    "tasks_due": len(due_tasks),
                    "blocked_tasks": sum(task.status == "BLOCKED" for task in open_tasks),
                    "overdue_tasks": sum(bool(task.due_date and task.due_date < day_end) for task in open_tasks),
                    "rooms_needing_service": affected_rooms,
                },
            })
        summary_cards = [
            {"label": "Open maintenance tasks", "value": len(open_tasks)},
            {"label": "Blocked tasks", "value": sum(task.status == "BLOCKED" for task in open_tasks)},
            {"label": "Overdue tasks", "value": sum(task.is_overdue for task in open_tasks)},
            {"label": "Rooms needing service", "value": affected_rooms},
        ]
        method_note = "This is scheduled maintenance workload from recorded tasks and room statuses. No unreported incidents are predicted."

    else:
        items = db.query(InventoryItem).filter(
            InventoryItem.resort_id == current_user.resort_id,
        ).order_by(InventoryItem.name).all()
        columns = [
            {"key": "items_tracked", "label": "Items tracked"},
            {"key": "items_at_reorder", "label": "At/below reorder level"},
            {"key": "projected_stockouts", "label": "Projected stockouts"},
        ]
        cumulative_consumption = {item.id: 0.0 for item in items}
        for day in occupancy_days:
            item_projection = []
            for item in items:
                daily_use = (item.consumption_rate_per_occupied_room or 0) * day["occupied_rooms"]
                cumulative_consumption[item.id] += daily_use
                projected_stock = max(0.0, item.current_stock - cumulative_consumption[item.id])
                item_projection.append({
                    "name": item.name,
                    "unit": item.unit,
                    "projected_stock": round(projected_stock, 2),
                    "reorder_threshold": item.reorder_threshold,
                    "daily_estimated_use": round(daily_use, 2),
                    "at_reorder": projected_stock <= item.reorder_threshold,
                    "stockout": projected_stock <= 0,
                })
            forecast_days.append({
                "date": day["date"],
                "day_name": day["day_name"],
                "metrics": {
                    "items_tracked": len(items),
                    "items_at_reorder": sum(item["at_reorder"] for item in item_projection),
                    "projected_stockouts": sum(item["stockout"] for item in item_projection),
                    "items": item_projection,
                },
            })
        final_projection = forecast_days[-1]["metrics"]["items"] if forecast_days else []
        summary_cards = [
            {"label": "Items tracked", "value": len(items)},
            {"label": f"At/below reorder in {days} days", "value": sum(item["at_reorder"] for item in final_projection)},
            {"label": f"Projected stockouts in {days} days", "value": sum(item["stockout"] for item in final_projection)},
        ]
        method_note = "Stock projections use each item's recorded consumption rate and projected occupied rooms. Availability and consumption rates are not live telemetry."

    return {
        "department": {"id": department.id, "name": department_name},
        "days": forecast_days,
        "columns": columns,
        "summary_cards": summary_cards,
        "method_note": method_note,
        "occupancy_context": occupancy_forecast.get("overall_summary", {}),
    }
