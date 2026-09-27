from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
from datetime import datetime, timedelta

from app.database.connection import get_db
from app.models import GuestRequest, Room, Task, Department, ActivityLog, User
from app.schemas import GuestRequestCreate, GuestRequestResponse, InternalGuestRequestCreate
from app.services.room_lifecycle import transition_room_status
from app.utils.auth import get_current_user, get_department_head_department_id

router = APIRouter(prefix="/api/guest-requests", tags=["Guest Requests"])

@router.post("", response_model=GuestRequestResponse)
def create_guest_request(
    request_in: GuestRequestCreate,
    db: Session = Depends(get_db)
):
    """
    Public / QR Code endpoint for guests to submit operational requests.
    Does NOT require internal staff login.
    """
    # Find resort and room
    room = db.query(Room).filter(Room.room_number == request_in.room_number).first()
    resort_id = room.resort_id if room else 1

    # Map request type to department
    dept_name = "Front Desk"
    req_lower = request_in.request_type.lower()
    if "ac" in req_lower or "maintenance" in req_lower or "plumb" in req_lower:
        dept_name = "Maintenance"
    elif "towel" in req_lower or "linen" in req_lower or "clean" in req_lower or "housekeeping" in req_lower:
        dept_name = "Housekeeping"
    elif "food" in req_lower or "service" in req_lower or "beverage" in req_lower or "dining" in req_lower:
        dept_name = "Food & Beverage"

    dept = db.query(Department).filter(
        and_(
            Department.resort_id == resort_id,
            Department.name.ilike(f"%{dept_name}%")
        )
    ).first()

    if room and dept_name == "Maintenance" and room.status != "maintenance":
        previous_room_status = room.status
        transition_room_status(room, "maintenance")
        db.add(ActivityLog(
            resort_id=resort_id,
            user_name=f"Guest (Room {request_in.room_number})",
            user_role="GUEST",
            action_type="ROOM_STATUS_CHANGED",
            entity_type="room",
            entity_id=room.id,
            description=f"Room {room.room_number} moved to maintenance after an AC/maintenance request",
            details_json={"old_status": previous_room_status, "new_status": "maintenance"},
        ))

    # Create guest request record
    guest_req = GuestRequest(
        resort_id=resort_id,
        room_id=room.id if room else None,
        room_number=request_in.room_number,
        guest_name=request_in.guest_name or "Guest",
        request_type=request_in.request_type,
        description=request_in.description,
        priority=request_in.priority or "MEDIUM",
        status="PENDING",
        source="GUEST_PORTAL"
    )
    db.add(guest_req)
    db.flush()

    # Automatically create operational task for the department
    sla_minutes = {"CRITICAL": 60, "HIGH": 120, "MEDIUM": 240, "LOW": 480}.get(
        request_in.priority or "MEDIUM", 240
    )
    task = Task(
        resort_id=resort_id,
        department_id=dept.id if dept else 1,
        title=f"Guest Request: Room {request_in.room_number} ({request_in.request_type})",
        description=f"Guest {request_in.guest_name or 'In-house'}: {request_in.description}",
        priority=request_in.priority or "MEDIUM",
        status="PENDING",
        room_number=request_in.room_number,
        sla_minutes=sla_minutes,
        due_date=datetime.utcnow() + timedelta(minutes=sla_minutes)
    )
    db.add(task)
    db.flush()

    guest_req.task_id = task.id

    # Activity Log
    log = ActivityLog(
        resort_id=resort_id,
        user_name=f"Guest (Room {request_in.room_number})",
        user_role="GUEST",
        action_type="GUEST_REQUEST_SUBMITTED",
        entity_type="guest_request",
        entity_id=guest_req.id,
        description=f"Guest in Room {request_in.room_number} submitted request: '{request_in.request_type}'. Task created for {dept_name}.",
        details_json={"room": request_in.room_number, "task_id": task.id}
    )
    db.add(log)
    db.commit()
    db.refresh(guest_req)

    return guest_req


@router.post("/internal", response_model=GuestRequestResponse)
def create_internal_guest_request(
    request_in: InternalGuestRequestCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a request reported by front desk or staff using the same request/task model."""
    if current_user.role not in {"MANAGER", "FRONT_DESK", "STAFF"}:
        raise HTTPException(status_code=403, detail="Role cannot create internal guest requests")
    if request_in.source.upper() not in {"VERBAL_STAFF", "FRONT_DESK", "PHONE", "EMAIL"}:
        raise HTTPException(status_code=400, detail="Invalid internal request source")

    room = db.query(Room).filter(Room.room_number == request_in.room_number).first()
    resort_id = current_user.resort_id
    if room and room.resort_id != resort_id:
        raise HTTPException(status_code=404, detail="Room not found in your resort")

    req_lower = request_in.request_type.lower()
    dept_name = "Front Desk"
    if any(term in req_lower for term in ["ac", "maintenance", "plumb"]):
        dept_name = "Maintenance"
    elif any(term in req_lower for term in ["towel", "linen", "clean", "housekeeping"]):
        dept_name = "Housekeeping"
    elif any(term in req_lower for term in ["food", "service", "beverage", "dining"]):
        dept_name = "Food & Beverage"
    dept = db.query(Department).filter(
        and_(Department.resort_id == resort_id, Department.name.ilike(f"%{dept_name}%"))
    ).first()
    if room and dept_name == "Maintenance" and room.status != "maintenance":
        previous_room_status = room.status
        transition_room_status(room, "maintenance")
        db.add(ActivityLog(
            resort_id=resort_id,
            user_id=current_user.id,
            user_name=current_user.name,
            user_role=current_user.role,
            action_type="ROOM_STATUS_CHANGED",
            entity_type="room",
            entity_id=room.id,
            description=f"Room {room.room_number} moved to maintenance after a reported issue",
            details_json={"old_status": previous_room_status, "new_status": "maintenance"},
        ))
    priority = request_in.priority or "MEDIUM"
    sla_minutes = {"CRITICAL": 60, "HIGH": 120, "MEDIUM": 240, "LOW": 480}.get(priority, 240)
    guest_req = GuestRequest(
        resort_id=resort_id,
        room_id=room.id if room else None,
        room_number=request_in.room_number,
        guest_name=request_in.guest_name or "Guest",
        request_type=request_in.request_type,
        description=request_in.description,
        priority=priority,
        status="PENDING",
        source=request_in.source.upper(),
        reported_by_user_id=request_in.reported_by_user_id or current_user.id,
    )
    db.add(guest_req)
    db.flush()
    task = Task(
        resort_id=resort_id,
        department_id=dept.id if dept else current_user.department_id or 1,
        title=f"Guest Request: Room {request_in.room_number} ({request_in.request_type})",
        description=f"Reported by {current_user.name}: {request_in.description}",
        priority=priority,
        status="PENDING",
        room_number=request_in.room_number,
        sla_minutes=sla_minutes,
        due_date=datetime.utcnow() + timedelta(minutes=sla_minutes),
    )
    db.add(task)
    db.flush()
    guest_req.task_id = task.id
    db.add(ActivityLog(
        resort_id=resort_id,
        user_id=current_user.id,
        user_name=current_user.name,
        user_role=current_user.role,
        action_type="GUEST_REQUEST_SUBMITTED",
        entity_type="guest_request",
        entity_id=guest_req.id,
        description=f"{current_user.name} submitted a {request_in.source.upper()} request for Room {request_in.room_number}",
        details_json={"source": request_in.source.upper(), "task_id": task.id, "department": dept_name},
    ))
    db.commit()
    db.refresh(guest_req)
    return guest_req


@router.get("", response_model=List[GuestRequestResponse])
def get_all_guest_requests(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Internal endpoint for staff to view all guest requests.
    """
    resort_id = current_user.resort_id

    query = db.query(GuestRequest).filter(
        GuestRequest.resort_id == resort_id,
        GuestRequest.is_training_sample.is_(False),
    )
    if current_user.role == "DEPARTMENT_HEAD":
        department_id = get_department_head_department_id(current_user)
        query = query.join(Task, GuestRequest.task_id == Task.id).filter(
            Task.department_id == department_id,
            Task.resort_id == resort_id,
        )
    if status:
        query = query.filter(GuestRequest.status == status.upper())

    return query.order_by(GuestRequest.created_at.desc()).all()


@router.patch("/{request_id}/status")
def update_guest_request_status(
    request_id: int,
    status: Optional[str] = None,
    status_payload: Optional[dict] = Body(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update guest request status (PENDING, IN_PROGRESS, COMPLETED).
    """
    resort_id = current_user.resort_id

    req = db.query(GuestRequest).filter(
        and_(GuestRequest.id == request_id, GuestRequest.resort_id == resort_id)
    ).first()

    if not req:
        raise HTTPException(status_code=404, detail="Guest request not found")

    if current_user.role == "DEPARTMENT_HEAD":
        department_id = get_department_head_department_id(current_user)
        if not req.task or req.task.department_id != department_id:
            raise HTTPException(status_code=403, detail="You can only update requests linked to your department")
        raise HTTPException(status_code=403, detail="Update the task from your department task dashboard")

    requested_status = status or (status_payload or {}).get("status")
    if not requested_status:
        raise HTTPException(status_code=400, detail="status is required")

    req.status = requested_status.upper()
    if req.status == "COMPLETED":
        req.completed_at = datetime.utcnow()
        if req.task:
            req.task.status = "COMPLETED"
            req.task.completed_at = datetime.utcnow()

    db.commit()

    return {"success": True, "request_id": req.id, "status": req.status}
