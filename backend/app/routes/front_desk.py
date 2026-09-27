from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models import ActivityLog, Booking, Department, Room, Task, User
from app.schemas import RoomResponse, RoomStatusUpdateRequest
from app.services.room_lifecycle import ROOM_STATUSES, ROOM_TRANSITIONS, transition_room_status
from app.utils.auth import require_role

router = APIRouter(prefix="/api", tags=["Front Desk & Rooms"])

@router.get("/rooms", response_model=list[RoomResponse])
def get_rooms(
    current_user: User = Depends(require_role(["FRONT_DESK"])),
    db: Session = Depends(get_db),
):
    return db.query(Room).filter(Room.resort_id == current_user.resort_id).order_by(Room.room_number).all()


@router.get("/rooms/status-transitions")
def get_room_status_transitions(
    current_user: User = Depends(require_role(["FRONT_DESK"])),
):
    return {status: sorted(next_statuses) for status, next_statuses in ROOM_TRANSITIONS.items()}


@router.patch("/rooms/{room_id}/status", response_model=RoomResponse)
def update_room_status(
    room_id: int,
    request: RoomStatusUpdateRequest,
    current_user: User = Depends(require_role(["FRONT_DESK"])),
    db: Session = Depends(get_db),
):
    room = db.query(Room).filter(
        Room.id == room_id,
        Room.resort_id == current_user.resort_id,
    ).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    old_status = room.status
    transition_room_status(room, request.status)
    db.add(ActivityLog(
        resort_id=current_user.resort_id,
        user_id=current_user.id,
        user_name=current_user.name,
        user_role=current_user.role,
        action_type="ROOM_STATUS_CHANGED",
        entity_type="room",
        entity_id=room.id,
        description=f"{current_user.name} changed Room {room.room_number} from {old_status} to {room.status}",
        details_json={"old_status": old_status, "new_status": room.status},
    ))
    db.commit()
    db.refresh(room)
    return room


@router.post("/front-desk/bookings/{booking_id}/check-in")
def check_in_booking(
    booking_id: int,
    current_user: User = Depends(require_role(["FRONT_DESK"])),
    db: Session = Depends(get_db),
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.resort_id == current_user.resort_id,
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != "confirmed":
        raise HTTPException(status_code=400, detail=f"Booking cannot be checked in from {booking.status}")
    if not booking.room_id or not booking.room:
        raise HTTPException(status_code=400, detail="Booking has no assigned room")
    if booking.room.status in {"maintenance", "out_of_service", "dirty"}:
        raise HTTPException(status_code=409, detail="Assigned room is not ready for check-in")

    booking.status = "checked_in"
    old_room_status = booking.room.status
    transition_room_status(booking.room, "occupied")
    db.add(ActivityLog(
        resort_id=current_user.resort_id,
        user_id=current_user.id,
        user_name=current_user.name,
        user_role=current_user.role,
        action_type="CHECK_IN",
        entity_type="booking",
        entity_id=booking.id,
        description=f"{current_user.name} checked {booking.guest_name} into Room {booking.room.room_number}",
        details_json={"room_id": booking.room.id, "old_room_status": old_room_status},
    ))
    db.commit()
    return {"success": True, "booking_id": booking.id, "status": booking.status, "room_status": booking.room.status}


@router.post("/front-desk/bookings/{booking_id}/check-out")
def check_out_booking(
    booking_id: int,
    current_user: User = Depends(require_role(["FRONT_DESK"])),
    db: Session = Depends(get_db),
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.resort_id == current_user.resort_id,
    ).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status != "checked_in":
        raise HTTPException(status_code=400, detail=f"Booking cannot be checked out from {booking.status}")

    booking.status = "checked_out"
    housekeeping_task = None
    old_room_status = booking.room.status if booking.room else None
    if booking.room:
        transition_room_status(booking.room, "dirty")
        housekeeping_department = db.query(Department).filter(
            Department.resort_id == current_user.resort_id,
            Department.name.ilike("%housekeeping%"),
        ).first()
        existing_task = db.query(Task).filter(
            Task.resort_id == current_user.resort_id,
            Task.room_number == booking.room.room_number,
            Task.title.ilike(f"%checkout%{booking.room.room_number}%"),
            Task.status.notin_(["COMPLETED", "CANCELLED"]),
        ).first()
        if not existing_task:
            housekeeping_task = Task(
                resort_id=current_user.resort_id,
                department_id=housekeeping_department.id if housekeeping_department else 1,
                title=f"Checkout cleaning - Room {booking.room.room_number}",
                description=f"Clean and inspect Room {booking.room.room_number} after {booking.guest_name}'s checkout.",
                priority="HIGH",
                status="PENDING",
                due_date=datetime.utcnow() + timedelta(minutes=120),
                sla_minutes=120,
                room_number=booking.room.room_number,
            )
            db.add(housekeeping_task)
            db.flush()

        db.add(ActivityLog(
            resort_id=current_user.resort_id,
            user_id=current_user.id,
            user_name=current_user.name,
            user_role=current_user.role,
            action_type="ROOM_STATUS_CHANGED",
            entity_type="room",
            entity_id=booking.room.id,
            description=f"Room {booking.room.room_number} changed from {old_room_status} to dirty after checkout",
            details_json={"old_status": old_room_status, "new_status": "dirty", "task_id": housekeeping_task.id if housekeeping_task else existing_task.id},
        ))
    db.add(ActivityLog(
        resort_id=current_user.resort_id,
        user_id=current_user.id,
        user_name=current_user.name,
        user_role=current_user.role,
        action_type="CHECK_OUT",
        entity_type="booking",
        entity_id=booking.id,
        description=f"{current_user.name} checked {booking.guest_name} out of Room {booking.room.room_number if booking.room else 'unassigned'}",
        details_json={"room_id": booking.room.id if booking.room else None, "housekeeping_task_id": housekeeping_task.id if housekeeping_task else existing_task.id if booking.room and existing_task else None},
    ))
    db.commit()
    return {
        "success": True,
        "booking_id": booking.id,
        "status": booking.status,
        "room_status": booking.room.status if booking.room else None,
        "housekeeping_task_id": housekeeping_task.id if housekeeping_task else existing_task.id if booking.room and existing_task else None,
        "completed_at": datetime.utcnow().isoformat(),
    }