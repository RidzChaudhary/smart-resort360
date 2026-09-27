import hashlib
import os
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    Booking,
    GuestAccount,
    GuestActivityInteraction,
    GuestBookingRequest,
    GuestFeedback,
    GuestProfile,
    GuestRequest,
    ResortActivity,
    Room,
)
from app.services.guest_intelligence import analyze_feedback, get_or_create_guest_profile
from app.utils.auth import get_password_hash


TRAINING_ACTIVITIES = [
    {
        "name": "Sunrise Yoga by the Pool",
        "description": "TRAINING SAMPLE: A guided morning yoga session by the resort pool.",
        "category": "Wellness",
        "tags": ["relaxation", "solo", "morning"],
        "capacity": 16,
        "crowd_level": "LOW",
    },
    {
        "name": "Coastal Kayak Tour",
        "description": "TRAINING SAMPLE: A small-group guided kayak trip along the coast.",
        "category": "Adventure",
        "tags": ["water", "group", "outdoors"],
        "capacity": 10,
        "crowd_level": "MODERATE",
    },
    {
        "name": "Local Flavors Cooking Class",
        "description": "TRAINING SAMPLE: A resort-hosted cooking class featuring local ingredients.",
        "category": "Dining",
        "tags": ["food", "family-friendly", "group"],
        "capacity": 12,
        "crowd_level": "MODERATE",
    },
    {
        "name": "Reef Discovery Snorkel",
        "description": "TRAINING SAMPLE: A guided beginner snorkel outing with resort equipment.",
        "category": "Adventure",
        "tags": ["water", "family-friendly", "outdoors"],
        "capacity": 8,
        "crowd_level": "HIGH",
    },
]

TRAINING_GUESTS = [
    ("wellness", 3, 5, 1, [0, 0, 1]),
    ("family", 2, 6, 4, [2, 3, 2]),
    ("adventure", 4, 12, 2, [1, 3, 1]),
    ("dining", 2, 4, 2, [2, 2, 2]),
    ("returning", 5, 16, 3, [0, 1, 3]),
    ("short-stay", 1, 2, 1, [0, 2, 0]),
]

TRAINING_FEEDBACK = [
    (0, "The instructor was friendly and the session was relaxing."),
    (1, "The tour guide was helpful and the kayak route was great."),
    (2, "The cooking class was enjoyable and the food was excellent."),
    (3, "The snorkel group was crowded and the wait was long."),
    (4, "The activity was great, but staff response was slow."),
    (5, "The class was clean, friendly, and wonderful."),
]

TRAINING_REQUESTS = [
    ("Housekeeping/Towels", "TRAINING SAMPLE: Please bring two extra pool towels.", "COMPLETED"),
    ("F&B/Room Service", "TRAINING SAMPLE: Please share the vegetarian dinner menu.", "IN_PROGRESS"),
    ("Amenities", "TRAINING SAMPLE: Please provide an additional water carafe.", "PENDING"),
]


def seed_guest_training_data(db: Session, resort_id: int) -> dict[str, int]:
    now = datetime.utcnow()
    booking = db.query(Booking).join(Room).filter(
        Booking.resort_id == resort_id,
        Booking.status == "checked_in",
        Booking.check_in <= now,
        Booking.check_out > now,
    ).order_by(Booking.check_out.desc()).first()
    if booking is None:
        return {"profiles": 0, "activities": 0, "interactions": 0, "feedback": 0, "requests": 0}

    guest_password = os.getenv("GUEST_DEMO_PASSWORD", "guest123")
    if os.getenv("APP_ENV", "development").strip().casefold() == "production" and len(guest_password) < 16:
        raise RuntimeError("GUEST_DEMO_PASSWORD must be at least 16 characters before production seeding")

    account = db.query(GuestAccount).filter(GuestAccount.email == "guest.demo@resort360.com").first()
    if account is None:
        account = GuestAccount(
            resort_id=resort_id,
            booking_id=booking.id,
            email="guest.demo@resort360.com",
            password_hash=get_password_hash(guest_password),
            active=True,
        )
        db.add(account)
    else:
        account.resort_id = resort_id
        account.booking_id = booking.id
        account.active = True
    demo_profile = get_or_create_guest_profile(db, booking)
    demo_profile.is_training_sample = True

    activities = []
    for values in TRAINING_ACTIVITIES:
        activity = db.query(ResortActivity).filter(
            ResortActivity.resort_id == resort_id,
            ResortActivity.name == values["name"],
        ).first()
        if activity is None:
            activity = ResortActivity(
                resort_id=resort_id,
                name=values["name"],
                description=values["description"],
                category=values["category"],
                tags=values["tags"],
                capacity=values["capacity"],
                available_slots=values["capacity"],
                crowd_level=values["crowd_level"],
                active=True,
                is_training_sample=True,
            )
            db.add(activity)
        else:
            activity.is_training_sample = True
        activities.append(activity)
    db.flush()

    profiles = []
    for index, (label, stays, nights, party_size, completed_activities) in enumerate(TRAINING_GUESTS):
        guest_key = hashlib.sha256(f"training:{resort_id}:{label}".encode("utf-8")).hexdigest()
        profile = db.query(GuestProfile).filter(
            GuestProfile.resort_id == resort_id,
            GuestProfile.guest_key == guest_key,
        ).first()
        if profile is None:
            profile = GuestProfile(
                resort_id=resort_id,
                guest_key=guest_key,
                total_stays=stays,
                total_nights=nights,
                average_party_size=float(party_size),
                segment="Synthetic Training",
                is_training_sample=True,
                preferred_categories=[],
                preferred_tags=[],
            )
            db.add(profile)
        else:
            profile.is_training_sample = True
        profiles.append((index, profile, completed_activities))
    db.flush()

    interaction_count = 0
    for profile_index, profile, activity_indexes in profiles:
        for activity_index in activity_indexes:
            activity = activities[activity_index]
            existing = db.query(GuestActivityInteraction).filter(
                GuestActivityInteraction.guest_profile_id == profile.id,
                GuestActivityInteraction.activity_id == activity.id,
                GuestActivityInteraction.is_training_sample.is_(True),
            ).first()
            if existing:
                continue
            for interaction_type, day_delta in (("BOOKED", 2), ("COMPLETED", 1)):
                db.add(GuestActivityInteraction(
                    resort_id=resort_id,
                    guest_profile_id=profile.id,
                    activity_id=activity.id,
                    interaction_type=interaction_type,
                    is_training_sample=True,
                    created_at=now - timedelta(days=day_delta + profile_index),
                ))
                interaction_count += 1
            if (profile_index + activity_index) % 2 == 0:
                db.add(GuestActivityInteraction(
                    resort_id=resort_id,
                    guest_profile_id=profile.id,
                    activity_id=activity.id,
                    interaction_type="RATED",
                    rating=5 if profile_index % 2 == 0 else 3,
                    is_training_sample=True,
                    created_at=now - timedelta(days=profile_index),
                ))
                interaction_count += 1

    feedback_count = 0
    for profile_index, comment in TRAINING_FEEDBACK:
        profile = profiles[profile_index][1]
        existing = db.query(GuestFeedback).filter(
            GuestFeedback.guest_profile_id == profile.id,
            GuestFeedback.comment == comment,
            GuestFeedback.is_training_sample.is_(True),
        ).first()
        if existing:
            continue
        sentiment, topics = analyze_feedback(comment)
        db.add(GuestFeedback(
            resort_id=resort_id,
            guest_profile_id=profile.id,
            activity_id=activities[profile_index % len(activities)].id,
            comment=comment,
            sentiment=sentiment,
            topics=topics,
            is_training_sample=True,
            created_at=now - timedelta(days=profile_index + 1),
        ))
        feedback_count += 1

    request_count = 0
    room = booking.room
    for request_type, description, status in TRAINING_REQUESTS:
        existing = db.query(GuestRequest).filter(
            GuestRequest.resort_id == resort_id,
            GuestRequest.room_id == room.id,
            GuestRequest.description == description,
            GuestRequest.is_training_sample.is_(True),
        ).first()
        if existing:
            continue
        request = GuestRequest(
            resort_id=resort_id,
            room_id=room.id,
            room_number=room.room_number,
            guest_name=booking.guest_name,
            request_type=request_type,
            description=description,
            priority="LOW",
            status=status,
            source="GUEST_PORTAL",
            is_training_sample=True,
            completed_at=now - timedelta(hours=3) if status == "COMPLETED" else None,
        )
        db.add(request)
        db.flush()
        db.add(GuestBookingRequest(
            resort_id=resort_id,
            booking_id=booking.id,
            guest_request_id=request.id,
            is_training_sample=True,
        ))
        request_count += 1

    db.flush()
    return {
        "profiles": len(profiles),
        "activities": len(activities),
        "interactions": interaction_count,
        "feedback": feedback_count,
        "requests": request_count,
    }
