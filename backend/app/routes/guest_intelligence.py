from datetime import datetime, timedelta
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models import (
    ActivityLog,
    Booking,
    Department,
    GuestActivityInteraction,
    GuestAccount,
    GuestBookingRequest,
    GuestFeedback,
    GuestProfile,
    GuestRequest,
    ResortActivity,
    Room,
    Task,
    User,
)
from app.schemas import (
    GuestActivityInteractionCreate,
    GuestFeedbackCreate,
    GuestLoginRequest,
    GuestProfileResponse,
    GuestRecommendationResponse,
    GuestServiceRequestCreate,
    GuestSessionRequest,
    ResortActivityCreate,
    ResortActivityUpdate,
)
from app.services.guest_intelligence import (
    analyze_feedback,
    get_or_create_guest_profile,
    manager_guest_intelligence,
    recommend_activities,
    refresh_stay_summary,
    serialize_activity,
    update_guest_segments,
)
from app.utils.auth import create_access_token, decode_access_token, require_role, verify_password

router = APIRouter(prefix="/api/guest-intelligence", tags=["Guest Intelligence"])
guest_security = HTTPBearer()
VALID_INTERACTIONS = {"VIEWED", "BOOKED", "COMPLETED", "CANCELLED", "RATED"}
VALID_CROWD_LEVELS = {"LOW", "MODERATE", "HIGH"}


def get_guest_booking(
    credentials: HTTPAuthorizationCredentials = Depends(guest_security),
    db: Session = Depends(get_db),
) -> Booking:
    try:
        payload = decode_access_token(credentials.credentials)
        if payload.get("role") != "GUEST":
            raise HTTPException(status_code=403, detail="Guest session required")
        booking_id = int(payload.get("sub", ""))
        resort_id = int(payload.get("resort_id", 0))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid guest session")
    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.resort_id == resort_id,
        Booking.status == "checked_in",
    ).first()
    if not booking or booking.check_out <= datetime.utcnow():
        raise HTTPException(status_code=401, detail="Guest stay is no longer active")
    return booking


def get_guest_context(booking: Booking, db: Session) -> tuple[GuestProfile, GuestProfileResponse]:
    profile = get_or_create_guest_profile(db, booking)
    update_guest_segments(db, booking.resort_id)
    db.commit()
    return profile, GuestProfileResponse(
        total_stays=profile.total_stays,
        total_nights=profile.total_nights,
        average_party_size=profile.average_party_size,
        preferred_categories=profile.preferred_categories or [],
        preferred_tags=profile.preferred_tags or [],
        segment=profile.segment,
    )


def _validated_crowd_level(value: str) -> str:
    normalized = value.upper()
    if normalized not in VALID_CROWD_LEVELS:
        raise HTTPException(status_code=400, detail="crowd_level must be LOW, MODERATE, or HIGH")
    return normalized


@router.post("/session")
def create_guest_session(request: GuestSessionRequest, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    bookings = db.query(Booking).join(Room).filter(
        Room.room_number == request.room_number.strip(),
        Booking.status == "checked_in",
        Booking.check_in <= now,
        Booking.check_out > now,
    ).all()
    supplied_name = re.sub(r"\s+", " ", request.guest_name.strip().casefold())
    booking = next((
        item for item in bookings
        if re.sub(r"\s+", " ", (item.guest_name or "").strip().casefold()) == supplied_name
    ), None)
    if booking is None:
        raise HTTPException(status_code=401, detail="Could not verify an active stay with those details")

    profile = get_or_create_guest_profile(db, booking)
    token = create_access_token(
        {"sub": str(booking.id), "role": "GUEST", "resort_id": booking.resort_id},
        expires_delta=timedelta(hours=12),
    )
    db.commit()
    return {
        "access_token": token,
        "token_type": "bearer",
        "guest": {"name": booking.guest_name},
        "profile": {
            "total_stays": profile.total_stays,
            "total_nights": profile.total_nights,
            "average_party_size": profile.average_party_size,
            "preferred_categories": profile.preferred_categories or [],
            "preferred_tags": profile.preferred_tags or [],
            "segment": profile.segment,
        },
    }


@router.post("/guest-login")
def guest_login(request: GuestLoginRequest, db: Session = Depends(get_db)):
    account = db.query(GuestAccount).filter(
        GuestAccount.email == request.email.strip().casefold(),
        GuestAccount.active.is_(True),
    ).first()
    if not account or not verify_password(request.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid guest email or password")
    booking = db.query(Booking).filter(
        Booking.id == account.booking_id,
        Booking.resort_id == account.resort_id,
        Booking.status == "checked_in",
        Booking.check_in <= datetime.utcnow(),
        Booking.check_out > datetime.utcnow(),
    ).first()
    if not booking:
        raise HTTPException(status_code=401, detail="Guest account has no active stay")
    profile = get_or_create_guest_profile(db, booking)
    token = create_access_token(
        {"sub": str(booking.id), "role": "GUEST", "resort_id": booking.resort_id},
        expires_delta=timedelta(hours=12),
    )
    db.commit()
    return {
        "access_token": token,
        "token_type": "bearer",
        "guest": {"name": booking.guest_name, "email": account.email},
        "profile": {
            "total_stays": profile.total_stays,
            "total_nights": profile.total_nights,
            "average_party_size": profile.average_party_size,
            "preferred_categories": profile.preferred_categories or [],
            "preferred_tags": profile.preferred_tags or [],
            "segment": profile.segment,
        },
    }


@router.get("/profiles/me", response_model=GuestProfileResponse)
def get_my_guest_profile(
    booking: Booking = Depends(get_guest_booking),
    db: Session = Depends(get_db),
):
    _, profile_response = get_guest_context(booking, db)
    return profile_response


@router.get("/activities")
def list_guest_activities(db: Session = Depends(get_db), booking: Booking = Depends(get_guest_booking)):
    now = datetime.utcnow()
    activities = db.query(ResortActivity).filter(
        ResortActivity.resort_id == booking.resort_id,
        ResortActivity.active.is_(True),
    ).all()
    profile = get_or_create_guest_profile(db, booking)
    interactions = db.query(GuestActivityInteraction).filter(
        GuestActivityInteraction.guest_profile_id == profile.id,
    ).order_by(GuestActivityInteraction.created_at, GuestActivityInteraction.id).all()
    latest_by_activity = {item.activity_id: item.interaction_type for item in interactions}
    return [serialize_activity(activity) | {"interaction_status": latest_by_activity.get(activity.id)}
            for activity in activities if not activity.end_at or activity.end_at >= now]


@router.get("/recommendations", response_model=list[GuestRecommendationResponse])
def get_guest_recommendations(
    limit: int = Query(5, ge=3, le=5),
    booking: Booking = Depends(get_guest_booking),
    db: Session = Depends(get_db),
):
    profile = get_or_create_guest_profile(db, booking)
    recommendations = recommend_activities(db, booking, profile, limit)
    db.commit()
    return recommendations


@router.get("/requests/me")
def get_my_requests(
    booking: Booking = Depends(get_guest_booking),
    db: Session = Depends(get_db),
):
    links = db.query(GuestBookingRequest).filter(
        GuestBookingRequest.booking_id == booking.id,
        GuestBookingRequest.resort_id == booking.resort_id,
    ).order_by(GuestBookingRequest.created_at.desc()).all()
    return [{
        "id": link.guest_request.id,
        "request_type": link.guest_request.request_type,
        "description": link.guest_request.description,
        "priority": link.guest_request.priority,
        "status": link.guest_request.status,
        "created_at": link.guest_request.created_at,
        "completed_at": link.guest_request.completed_at,
        "is_training_sample": link.is_training_sample,
    } for link in links]


@router.post("/requests")
def create_my_request(
    request: GuestServiceRequestCreate,
    booking: Booking = Depends(get_guest_booking),
    db: Session = Depends(get_db),
):
    priority = request.priority.upper()
    if priority not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        raise HTTPException(status_code=400, detail="Unsupported request priority")
    room = db.query(Room).filter(
        Room.id == booking.room_id,
        Room.resort_id == booking.resort_id,
    ).first()
    if room is None:
        raise HTTPException(status_code=409, detail="The active stay has no assigned room")

    request_type = request.request_type.strip()
    request_text = f"{request_type} {request.description}".casefold()
    department_name = "Front Desk"
    if any(term in request_text for term in ("ac", "maintenance", "plumb", "repair")):
        department_name = "Maintenance"
    elif any(term in request_text for term in ("towel", "linen", "clean", "housekeeping", "room cleaning")):
        department_name = "Housekeeping"
    elif any(term in request_text for term in ("food", "service", "beverage", "dining", "meal")):
        department_name = "Food & Beverage"
    department = db.query(Department).filter(
        Department.resort_id == booking.resort_id,
        Department.name == department_name,
    ).first()
    if department is None:
        raise HTTPException(status_code=409, detail="The request department is not configured")

    sla_minutes = {"CRITICAL": 60, "HIGH": 120, "MEDIUM": 240, "LOW": 480}[priority]
    guest_request = GuestRequest(
        resort_id=booking.resort_id,
        room_id=room.id,
        room_number=room.room_number,
        guest_name=booking.guest_name,
        request_type=request_type,
        description=request.description.strip(),
        priority=priority,
        status="PENDING",
        source="GUEST_PORTAL",
    )
    db.add(guest_request)
    db.flush()
    task = Task(
        resort_id=booking.resort_id,
        department_id=department.id,
        title=f"Guest Request: Room {room.room_number} ({request_type})",
        description=f"Guest {booking.guest_name}: {request.description.strip()}",
        priority=priority,
        status="PENDING",
        room_number=room.room_number,
        sla_minutes=sla_minutes,
        due_date=datetime.utcnow() + timedelta(minutes=sla_minutes),
    )
    db.add(task)
    db.flush()
    guest_request.task_id = task.id
    link = GuestBookingRequest(
        resort_id=booking.resort_id,
        booking_id=booking.id,
        guest_request_id=guest_request.id,
    )
    db.add(link)
    db.add(ActivityLog(
        resort_id=booking.resort_id,
        user_name=f"Guest (Room {room.room_number})",
        user_role="GUEST",
        action_type="GUEST_REQUEST_SUBMITTED",
        entity_type="guest_request",
        entity_id=guest_request.id,
        description=f"Guest in Room {room.room_number} submitted a service request for {department_name}.",
        details_json={"task_id": task.id, "department": department_name},
    ))
    db.commit()
    return {
        "id": guest_request.id,
        "request_type": guest_request.request_type,
        "description": guest_request.description,
        "priority": guest_request.priority,
        "status": guest_request.status,
        "created_at": guest_request.created_at,
        "is_training_sample": False,
    }


@router.get("/manager/activities")
def list_manager_activities(
    current_user: User = Depends(require_role(["MANAGER"])),
    db: Session = Depends(get_db),
):
    activities = db.query(ResortActivity).filter(
        ResortActivity.resort_id == current_user.resort_id,
    ).order_by(ResortActivity.category, ResortActivity.name).all()
    return [serialize_activity(activity) | {"active": activity.active} for activity in activities]


@router.post("/manager/activities")
def create_activity(
    request: ResortActivityCreate,
    current_user: User = Depends(require_role(["MANAGER"])),
    db: Session = Depends(get_db),
):
    crowd_level = _validated_crowd_level(request.crowd_level)
    slots = request.capacity if request.available_slots is None else request.available_slots
    if slots > request.capacity:
        raise HTTPException(status_code=400, detail="available_slots cannot exceed capacity")
    if request.start_at and request.end_at and request.end_at <= request.start_at:
        raise HTTPException(status_code=400, detail="end_at must be after start_at")
    activity = ResortActivity(
        resort_id=current_user.resort_id,
        name=request.name.strip(),
        description=request.description.strip(),
        category=request.category.strip(),
        tags=[tag.strip() for tag in request.tags if tag.strip()],
        capacity=request.capacity,
        available_slots=slots,
        start_at=request.start_at,
        end_at=request.end_at,
        crowd_level=crowd_level,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return serialize_activity(activity) | {"active": activity.active}


@router.patch("/manager/activities/{activity_id}")
def update_activity(
    activity_id: int,
    request: ResortActivityUpdate,
    current_user: User = Depends(require_role(["MANAGER"])),
    db: Session = Depends(get_db),
):
    activity = db.query(ResortActivity).filter(
        ResortActivity.id == activity_id,
        ResortActivity.resort_id == current_user.resort_id,
    ).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    updates = request.model_dump(exclude_unset=True)
    if "crowd_level" in updates and updates["crowd_level"] is not None:
        updates["crowd_level"] = _validated_crowd_level(updates["crowd_level"])
    new_capacity = updates.get("capacity", activity.capacity)
    new_slots = updates.get("available_slots", activity.available_slots)
    if new_slots > new_capacity:
        raise HTTPException(status_code=400, detail="available_slots cannot exceed capacity")
    start_at = updates.get("start_at", activity.start_at)
    end_at = updates.get("end_at", activity.end_at)
    if start_at and end_at and end_at <= start_at:
        raise HTTPException(status_code=400, detail="end_at must be after start_at")
    for field, value in updates.items():
        if field in {"name", "description", "category"} and value is not None:
            value = value.strip()
        if field == "tags" and value is not None:
            value = [tag.strip() for tag in value if tag.strip()]
        setattr(activity, field, value)
    db.commit()
    db.refresh(activity)
    return serialize_activity(activity) | {"active": activity.active}


@router.post("/interactions")
def create_interaction(
    request: GuestActivityInteractionCreate,
    booking: Booking = Depends(get_guest_booking),
    db: Session = Depends(get_db),
):
    interaction_type = request.interaction_type.upper()
    if interaction_type not in VALID_INTERACTIONS:
        raise HTTPException(status_code=400, detail=f"interaction_type must be one of {sorted(VALID_INTERACTIONS)}")
    activity = db.query(ResortActivity).filter(
        ResortActivity.id == request.activity_id,
        ResortActivity.resort_id == booking.resort_id,
        ResortActivity.active.is_(True),
    ).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    profile = get_or_create_guest_profile(db, booking)
    latest = db.query(GuestActivityInteraction).filter(
        GuestActivityInteraction.guest_profile_id == profile.id,
        GuestActivityInteraction.activity_id == activity.id,
    ).order_by(GuestActivityInteraction.created_at.desc(), GuestActivityInteraction.id.desc()).first()

    if interaction_type == "RATED" and request.rating is None:
        raise HTTPException(status_code=400, detail="rating from 1 to 5 is required for RATED")
    if interaction_type != "RATED" and request.rating is not None:
        raise HTTPException(status_code=400, detail="rating is only accepted for RATED interactions")
    if interaction_type == "BOOKED":
        if activity.available_slots < 1:
            raise HTTPException(status_code=409, detail="No activity places are currently available")
        if latest and latest.interaction_type == "BOOKED":
            raise HTTPException(status_code=409, detail="This activity is already booked for your profile")
        activity.available_slots -= 1
    elif interaction_type == "CANCELLED":
        if not latest or latest.interaction_type != "BOOKED":
            raise HTTPException(status_code=409, detail="There is no active booking to cancel")
        activity.available_slots = min(activity.available_slots + 1, activity.capacity)
    elif interaction_type == "COMPLETED" and (not latest or latest.interaction_type != "BOOKED"):
        raise HTTPException(status_code=409, detail="Only a booked activity can be marked completed")
    elif interaction_type == "RATED" and (not latest or latest.interaction_type not in {"COMPLETED", "RATED"}):
        raise HTTPException(status_code=409, detail="An activity can be rated after it is completed")

    interaction = GuestActivityInteraction(
        resort_id=booking.resort_id,
        guest_profile_id=profile.id,
        activity_id=activity.id,
        interaction_type=interaction_type,
        rating=request.rating,
    )
    db.add(interaction)
    db.flush()
    refresh_stay_summary(db, profile)
    update_guest_segments(db, booking.resort_id)
    db.commit()
    return {"id": interaction.id, "activity_id": activity.id, "interaction_type": interaction_type, "available_slots": activity.available_slots}


@router.post("/feedback")
def create_feedback(
    request: GuestFeedbackCreate,
    booking: Booking = Depends(get_guest_booking),
    db: Session = Depends(get_db),
):
    profile = get_or_create_guest_profile(db, booking)
    update_guest_segments(db, booking.resort_id)
    activity = None
    if request.activity_id is not None:
        activity = db.query(ResortActivity).filter(
            ResortActivity.id == request.activity_id,
            ResortActivity.resort_id == booking.resort_id,
        ).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found")
    sentiment, topics = analyze_feedback(request.comment)
    feedback = GuestFeedback(
        resort_id=booking.resort_id,
        guest_profile_id=profile.id,
        activity_id=activity.id if activity else None,
        comment=request.comment.strip(),
        sentiment=sentiment,
        topics=topics,
    )
    db.add(feedback)
    db.commit()
    return {"id": feedback.id, "sentiment": sentiment, "topics": topics}


@router.get("/manager/overview")
def get_manager_overview(
    current_user: User = Depends(require_role(["MANAGER"])),
    db: Session = Depends(get_db),
):
    overview = manager_guest_intelligence(db, current_user.resort_id)
    db.commit()
    return overview
