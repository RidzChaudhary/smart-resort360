import hashlib
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from app.models import (
    Booking,
    GuestActivityInteraction,
    GuestBookingRequest,
    GuestFeedback,
    GuestProfile,
    ResortActivity,
)


def guest_key_for_booking(booking: Booking) -> str:
    email = (booking.guest_email or "").strip().casefold()
    if email and email not in {"guest@example.com", "guest@resort360.com"}:
        identity = f"email:{email}"
    else:
        normalized_name = re.sub(r"\s+", " ", (booking.guest_name or "").strip().casefold())
        identity = f"name:{normalized_name}"
    return hashlib.sha256(f"{booking.resort_id}:{identity}".encode("utf-8")).hexdigest()


def get_or_create_guest_profile(db: Session, booking: Booking) -> GuestProfile:
    key = guest_key_for_booking(booking)
    profile = db.query(GuestProfile).filter(
        GuestProfile.resort_id == booking.resort_id,
        GuestProfile.guest_key == key,
    ).first()
    if profile is None:
        profile = GuestProfile(resort_id=booking.resort_id, guest_key=key)
        db.add(profile)
        db.flush()
    refresh_stay_summary(db, profile)
    return profile


def refresh_stay_summary(db: Session, profile: GuestProfile) -> None:
    bookings = db.query(Booking).filter(Booking.resort_id == profile.resort_id).all()
    matching = [booking for booking in bookings if guest_key_for_booking(booking) == profile.guest_key]
    matching = [booking for booking in matching if booking.status not in {"cancelled", "no_show"}]
    profile.total_stays = len(matching)
    profile.total_nights = sum(max((booking.check_out.date() - booking.check_in.date()).days, 0) for booking in matching)
    profile.average_party_size = round(float(np.mean([booking.guests_count or 1 for booking in matching])) if matching else 1.0, 2)

    interactions = db.query(GuestActivityInteraction).filter(
        GuestActivityInteraction.guest_profile_id == profile.id,
        GuestActivityInteraction.interaction_type.in_(["BOOKED", "COMPLETED", "RATED"]),
    ).all()
    category_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    guest_activities = {activity.id: activity for activity in db.query(ResortActivity).filter(
        ResortActivity.resort_id == profile.resort_id,
    ).all()}
    for interaction in interactions:
        activity = guest_activities.get(interaction.activity_id)
        if activity is None:
            continue
        weight = 2 if interaction.interaction_type == "COMPLETED" else 1
        category_counts[activity.category] += weight
        for tag in (activity.tags or []):
            tag_counts[str(tag)] += weight
    profile.preferred_categories = [value for value, _ in category_counts.most_common(5)]
    profile.preferred_tags = [value for value, _ in tag_counts.most_common(8)]
    profile.updated_at = datetime.utcnow()


def _profile_features(db: Session, profiles: list[GuestProfile]) -> np.ndarray:
    features = []
    for profile in profiles:
        interaction_count = db.query(GuestActivityInteraction).filter(
            GuestActivityInteraction.guest_profile_id == profile.id,
            GuestActivityInteraction.interaction_type.in_(["BOOKED", "COMPLETED"]),
        ).count()
        completed_count = db.query(GuestActivityInteraction).filter(
            GuestActivityInteraction.guest_profile_id == profile.id,
            GuestActivityInteraction.interaction_type == "COMPLETED",
        ).count()
        features.append([
            profile.total_stays,
            profile.total_nights,
            profile.average_party_size,
            interaction_count,
            completed_count,
        ])
    return np.asarray(features, dtype=float)


# ─── Segment label heuristics ────────────────────────────────────────────────
_WELLNESS_TAGS = {"wellness", "relaxation", "spa", "yoga", "meditation", "health"}
_FAMILY_TAGS = {"family", "family-friendly", "kids", "children", "group"}
_ADVENTURE_TAGS = {"adventure", "water", "outdoors", "sports", "hiking", "kayak"}
_ROMANTIC_TAGS = {"romantic", "couples", "sunset", "intimate"}
_FOOD_TAGS = {"food", "dining", "cooking", "culinary", "restaurant"}
_LUXURY_TAGS = {"luxury", "premium", "exclusive", "vip"}


def _infer_segment_label(profiles_in_cluster: list[GuestProfile], all_interactions: dict[int, list], all_activities: dict[int, ResortActivity]) -> str:
    """Derive a meaningful segment label from the actual behavioral patterns of the cluster."""
    tag_votes: Counter[str] = Counter()
    category_votes: Counter[str] = Counter()
    for profile in profiles_in_cluster:
        for tag in (profile.preferred_tags or []):
            tag_votes[tag.lower()] += 1
        for cat in (profile.preferred_categories or []):
            category_votes[cat.lower()] += 1
        for interaction in all_interactions.get(profile.id, []):
            activity = all_activities.get(interaction.activity_id)
            if activity:
                category_votes[activity.category.lower()] += 1
                for tag in (activity.tags or []):
                    tag_votes[tag.lower()] += 1

    # Score each archetype
    wellness = sum(tag_votes[t] for t in _WELLNESS_TAGS) + category_votes.get("wellness", 0)
    family = sum(tag_votes[t] for t in _FAMILY_TAGS)
    adventure = sum(tag_votes[t] for t in _ADVENTURE_TAGS) + category_votes.get("adventure", 0)
    romantic = sum(tag_votes[t] for t in _ROMANTIC_TAGS)
    food = sum(tag_votes[t] for t in _FOOD_TAGS) + category_votes.get("dining", 0)
    luxury = sum(tag_votes[t] for t in _LUXURY_TAGS)

    scores = {
        "WELLNESS": wellness,
        "FAMILY": family,
        "ADVENTURE": adventure,
        "ROMANTIC": romantic,
        "FOOD": food,
        "LUXURY": luxury,
    }
    best = max(scores, key=lambda k: scores[k])
    if scores[best] == 0:
        # Fallback to stay length heuristic
        avg_nights = float(np.mean([p.total_nights for p in profiles_in_cluster])) if profiles_in_cluster else 0
        if avg_nights >= 5:
            return "LUXURY"
        elif avg_nights >= 3:
            return "WELLNESS"
        else:
            return "ADVENTURE"
    return best


def update_guest_segments(db: Session, resort_id: int) -> list[GuestProfile]:
    profiles = db.query(GuestProfile).filter(GuestProfile.resort_id == resort_id).order_by(GuestProfile.id).all()
    if not profiles:
        return profiles
    if len(profiles) < 3:
        for profile in profiles:
            profile.segment = "RETURNING" if profile.total_stays > 1 else "NEW GUEST"
        db.flush()
        return profiles

    features = _profile_features(db, profiles)
    scaled = StandardScaler().fit_transform(features)
    cluster_count = min(6, len(profiles))
    labels = KMeans(n_clusters=cluster_count, random_state=42, n_init=10).fit_predict(scaled)

    # Group profiles by cluster label
    clusters: dict[int, list[GuestProfile]] = defaultdict(list)
    for profile, label in zip(profiles, labels):
        clusters[int(label)].append(profile)

    # Load interaction and activity data for label inference
    all_interactions: dict[int, list] = defaultdict(list)
    for interaction in db.query(GuestActivityInteraction).filter(
        GuestActivityInteraction.resort_id == resort_id,
        GuestActivityInteraction.interaction_type.in_(["BOOKED", "COMPLETED"]),
    ).all():
        all_interactions[interaction.guest_profile_id].append(interaction)

    all_activities = {a.id: a for a in db.query(ResortActivity).filter(ResortActivity.resort_id == resort_id).all()}

    # Assign meaningful labels with deduplication
    used_labels: dict[str, int] = {}
    for label_idx, cluster_profiles in clusters.items():
        segment_name = _infer_segment_label(cluster_profiles, all_interactions, all_activities)
        # If label already used, append index to differentiate
        if segment_name in used_labels:
            used_labels[segment_name] += 1
            display_name = segment_name
        else:
            used_labels[segment_name] = 1
            display_name = segment_name
        for profile in cluster_profiles:
            profile.segment = display_name

    db.flush()
    return profiles


def _similar_guest_activity_scores(db: Session, profile: GuestProfile) -> tuple[dict[int, float], bool]:
    profiles = db.query(GuestProfile).filter(
        GuestProfile.resort_id == profile.resort_id,
        GuestProfile.id != profile.id,
    ).all()
    if not profiles:
        return {}, False
    candidates = [profile, *profiles]
    features = _profile_features(db, candidates)
    scaled = StandardScaler().fit_transform(features)
    neighbors = NearestNeighbors(n_neighbors=min(4, len(candidates)), metric="euclidean")
    neighbors.fit(scaled)
    _, indices = neighbors.kneighbors(scaled[:1])
    neighbor_ids = {candidates[index].id for index in indices[0] if candidates[index].id != profile.id}
    if not neighbor_ids:
        return {}, False

    interactions = db.query(GuestActivityInteraction).filter(
        GuestActivityInteraction.guest_profile_id.in_(neighbor_ids),
        GuestActivityInteraction.interaction_type.in_(["BOOKED", "COMPLETED", "RATED"]),
    ).all()
    scores: defaultdict[int, float] = defaultdict(float)
    for interaction in interactions:
        weight = 1.0 if interaction.interaction_type == "BOOKED" else 1.5
        if interaction.rating:
            weight *= max(interaction.rating - 1, 0) / 4
        scores[interaction.activity_id] += weight
    uses_training = any(candidate.id in neighbor_ids and candidate.is_training_sample for candidate in profiles)
    return dict(scores), uses_training


def recommend_activities(
    db: Session,
    booking: Booking,
    profile: GuestProfile,
    limit: int = 5,
) -> list[dict[str, Any]]:
    now = datetime.utcnow()
    query = db.query(ResortActivity).filter(
        ResortActivity.resort_id == booking.resort_id,
        ResortActivity.active.is_(True),
        ResortActivity.available_slots > 0,
    )
    activities = [activity for activity in query.all() if not activity.end_at or activity.end_at >= now]
    if not activities:
        return []

    interactions = db.query(GuestActivityInteraction).filter(
        GuestActivityInteraction.guest_profile_id == profile.id,
    ).order_by(GuestActivityInteraction.created_at, GuestActivityInteraction.id).all()
    activity_history: defaultdict[int, list[GuestActivityInteraction]] = defaultdict(list)
    for interaction in interactions:
        activity_history[interaction.activity_id].append(interaction)
    category_history: Counter[str] = Counter()
    tag_history: Counter[str] = Counter()
    for interaction in interactions:
        if interaction.interaction_type in {"BOOKED", "COMPLETED", "RATED"}:
            activity = db.query(ResortActivity).filter(ResortActivity.id == interaction.activity_id).first()
            if activity:
                category_history[activity.category] += 2 if interaction.interaction_type == "COMPLETED" else 1
                for tag in (activity.tags or []):
                    tag_history[str(tag)] += 2 if interaction.interaction_type == "COMPLETED" else 1

    similar_scores, similar_uses_training = _similar_guest_activity_scores(db, profile)
    ratings = db.query(GuestActivityInteraction).filter(
        GuestActivityInteraction.resort_id == booking.resort_id,
        GuestActivityInteraction.interaction_type == "RATED",
        GuestActivityInteraction.rating.isnot(None),
    ).all()
    activity_ratings: defaultdict[int, list[int]] = defaultdict(list)
    training_rated_activities = set()
    for rating in ratings:
        activity_ratings[rating.activity_id].append(rating.rating)
        if rating.is_training_sample:
            training_rated_activities.add(rating.activity_id)

    remaining_nights = max((booking.check_out.date() - now.date()).days, 0)
    ranked = []
    for activity in activities:
        history = activity_history.get(activity.id, [])
        if history and history[-1].interaction_type == "BOOKED":
            continue
        score = 0.0
        reasons = []
        if category_history.get(activity.category):
            score += min(category_history[activity.category] * 0.08, 0.28)
            reasons.append(f"Based on your past interest in {activity.category}")
        matched_tags = [tag for tag in (activity.tags or []) if tag_history.get(str(tag))]
        if matched_tags:
            score += min(sum(tag_history[str(tag)] for tag in matched_tags) * 0.04, 0.16)
            reasons.append(f"Matches tags from activities you booked or completed: {', '.join(matched_tags[:2])}")
        if similar_scores.get(activity.id):
            score += min(similar_scores[activity.id] * 0.06, 0.24)
            if similar_uses_training:
                reasons.append("Similar stay patterns include labeled synthetic training examples")
            else:
                reasons.append("Guests with similar stay patterns booked or completed this activity")
        if activity.start_at and activity.start_at.date() <= booking.check_out.date():
            if activity.start_at.date() >= now.date():
                score += 0.12
                reasons.append("Scheduled during your current stay")
        if activity.start_at and activity.start_at.date() > booking.check_out.date():
            continue
        if booking.guests_count >= 3 and any(tag.casefold() in {"family", "group", "family-friendly"} for tag in (activity.tags or [])):
            score += 0.1
            reasons.append("Tagged as suitable for groups")
        if booking.guests_count == 1 and any(tag.casefold() in {"solo", "small-group", "relaxation"} for tag in (activity.tags or [])):
            score += 0.06
            reasons.append("Tagged for a smaller group")
        if activity.crowd_level == "LOW":
            score += 0.08
            reasons.append("Currently marked as a lower-crowd option")
        elif activity.crowd_level == "HIGH":
            score -= 0.08
            reasons.append("Crowd level is marked high")
        if activity_ratings.get(activity.id):
            average_rating = float(np.mean(activity_ratings[activity.id]))
            score += (average_rating - 3.0) * 0.035
            if activity.id in training_rated_activities:
                reasons.append(f"Demo training rating average: {average_rating:.1f}/5")
            else:
                reasons.append(f"Guest rating average: {average_rating:.1f}/5")
        score += min(activity.available_slots / max(activity.capacity, 1), 1.0) * 0.08
        reasons.append(f"{activity.available_slots} of {activity.capacity} places currently listed as available")
        if remaining_nights <= 1 and activity.start_at and (activity.start_at.date() - now.date()).days > remaining_nights:
            continue
        ranked.append({
            "activity": serialize_activity(activity),
            "score": round(score, 3),
            "reasons": reasons[:4],
        })

    ranked.sort(key=lambda item: (item["score"], item["activity"]["available_slots"]), reverse=True)
    return ranked[:max(3, min(limit, 5))]


def serialize_activity(activity: ResortActivity) -> dict[str, Any]:
    return {
        "id": activity.id,
        "name": activity.name,
        "description": activity.description,
        "category": activity.category,
        "tags": activity.tags or [],
        "capacity": activity.capacity,
        "available_slots": activity.available_slots,
        "start_at": activity.start_at.isoformat() if activity.start_at else None,
        "end_at": activity.end_at.isoformat() if activity.end_at else None,
        "crowd_level": activity.crowd_level,
        "is_training_sample": activity.is_training_sample,
    }


_SENTIMENT_TERMS = {
    "positive": {"great", "excellent", "loved", "wonderful", "helpful", "enjoyed", "amazing", "friendly", "clean", "relaxing", "beautiful", "fantastic", "perfect", "superb", "outstanding"},
    "negative": {"bad", "poor", "rude", "dirty", "late", "slow", "crowded", "broken", "disappointed", "unhelpful", "noisy", "terrible", "awful", "horrible", "worst"},
}
_TOPIC_TERMS = {
    "service": {"staff", "service", "help", "friendly", "rude", "response", "attentive"},
    "wait_time": {"wait", "late", "slow", "delay", "long", "queue"},
    "cleanliness": {"clean", "dirty", "tidy", "hygiene", "spotless"},
    "crowding": {"crowd", "crowded", "busy", "packed", "full"},
    "activity_quality": {"activity", "tour", "class", "equipment", "instructor", "guide"},
    "food": {"food", "meal", "breakfast", "dinner", "restaurant", "cuisine", "taste"},
    "experience": {"experience", "enjoyable", "loved", "relaxing", "relaxation", "wonderful", "amazing"},
    "location": {"location", "view", "beach", "pool", "garden", "resort", "beautiful"},
}


def analyze_feedback(comment: str) -> tuple[str, list[str]]:
    words = set(re.findall(r"[a-z]+", comment.casefold()))
    positive = len(words & _SENTIMENT_TERMS["positive"])
    negative = len(words & _SENTIMENT_TERMS["negative"])
    if positive > 0 and negative > 0:
        sentiment = "MIXED"
    elif positive > negative:
        sentiment = "POSITIVE"
    elif negative > positive:
        sentiment = "NEGATIVE"
    else:
        sentiment = "NEUTRAL"
    topics = [topic for topic, terms in _TOPIC_TERMS.items() if words & terms]
    return sentiment, topics or ["general"]


def _build_segment_analytics(
    db: Session,
    resort_id: int,
    profiles: list[GuestProfile],
    since: datetime,
) -> list[dict[str, Any]]:
    """Build rich per-segment analytics: guest count, avg satisfaction, top activities."""
    # Group profiles by segment
    segment_profiles: defaultdict[str, list[GuestProfile]] = defaultdict(list)
    for profile in profiles:
        segment_profiles[profile.segment].append(profile)

    # Fetch all interactions + ratings for profiles
    all_profile_ids = [p.id for p in profiles]
    interactions = []
    if all_profile_ids:
        interactions = db.query(GuestActivityInteraction).filter(
            GuestActivityInteraction.guest_profile_id.in_(all_profile_ids),
            GuestActivityInteraction.interaction_type.in_(["BOOKED", "COMPLETED", "RATED"]),
        ).all()

    # Map interactions by profile
    profile_interactions: defaultdict[int, list] = defaultdict(list)
    for interaction in interactions:
        profile_interactions[interaction.guest_profile_id].append(interaction)

    # Load all activities
    all_activities = {a.id: a for a in db.query(ResortActivity).filter(ResortActivity.resort_id == resort_id).all()}

    # Fetch all ratings for satisfaction scoring
    all_ratings = db.query(GuestActivityInteraction).filter(
        GuestActivityInteraction.resort_id == resort_id,
        GuestActivityInteraction.interaction_type == "RATED",
        GuestActivityInteraction.rating.isnot(None),
    ).all()
    activity_avg_ratings: defaultdict[int, list[float]] = defaultdict(list)
    for r in all_ratings:
        if r.rating:
            activity_avg_ratings[r.activity_id].append(float(r.rating))

    result = []
    for segment_name, seg_profiles in sorted(segment_profiles.items()):
        # Count activity interactions per activity for this segment
        activity_counter: Counter[int] = Counter()
        rating_sum = 0.0
        rating_count = 0

        for profile in seg_profiles:
            for interaction in profile_interactions.get(profile.id, []):
                if interaction.interaction_type in {"BOOKED", "COMPLETED"}:
                    activity_counter[interaction.activity_id] += 1
                if interaction.interaction_type == "RATED" and interaction.rating:
                    rating_sum += float(interaction.rating)
                    rating_count += 1

        # Top activities
        top_activity_ids = [aid for aid, _ in activity_counter.most_common(3)]
        top_activities = []
        for aid in top_activity_ids:
            activity = all_activities.get(aid)
            if activity:
                avg_rating = round(float(np.mean(activity_avg_ratings[aid])), 2) if activity_avg_ratings[aid] else None
                top_activities.append({
                    "id": aid,
                    "name": activity.name,
                    "category": activity.category,
                    "count": activity_counter[aid],
                    "avg_rating": avg_rating,
                })

        avg_satisfaction = round(rating_sum / rating_count, 2) if rating_count > 0 else None

        result.append({
            "name": segment_name,
            "guest_count": len(seg_profiles),
            "avg_satisfaction": avg_satisfaction,
            "top_activities": top_activities,
        })

    return result


def _build_recommendation_performance(
    db: Session,
    resort_id: int,
) -> dict[str, Any]:
    """Build recommendation performance metrics from interaction data."""
    total_interactions = db.query(GuestActivityInteraction).filter(
        GuestActivityInteraction.resort_id == resort_id,
    ).count()

    booked = db.query(GuestActivityInteraction).filter(
        GuestActivityInteraction.resort_id == resort_id,
        GuestActivityInteraction.interaction_type == "BOOKED",
    ).count()

    completed = db.query(GuestActivityInteraction).filter(
        GuestActivityInteraction.resort_id == resort_id,
        GuestActivityInteraction.interaction_type == "COMPLETED",
    ).count()

    viewed = db.query(GuestActivityInteraction).filter(
        GuestActivityInteraction.resort_id == resort_id,
        GuestActivityInteraction.interaction_type == "VIEWED",
    ).count()

    # Activity-level recommendation counts (top recommended activities)
    all_interactions = db.query(GuestActivityInteraction).filter(
        GuestActivityInteraction.resort_id == resort_id,
    ).all()
    activity_counts: Counter[int] = Counter(i.activity_id for i in all_interactions)
    all_activities = {a.id: a for a in db.query(ResortActivity).filter(ResortActivity.resort_id == resort_id).all()}

    top_recommended = []
    for activity_id, count in activity_counts.most_common(5):
        activity = all_activities.get(activity_id)
        if activity:
            top_recommended.append({
                "name": activity.name,
                "count": count,
                "category": activity.category,
            })

    acceptance_rate = round((booked / max(viewed + booked, 1)) * 100, 1) if (viewed + booked) > 0 else 0.0
    completion_rate = round((completed / max(booked, 1)) * 100, 1) if booked > 0 else 0.0

    status_breakdown: Counter[str] = Counter()
    for interaction in all_interactions:
        status_breakdown[interaction.interaction_type] += 1

    return {
        "total_generated": total_interactions,
        "booked": booked,
        "completed": completed,
        "viewed": viewed,
        "acceptance_rate": acceptance_rate,
        "completion_rate": completion_rate,
        "status_breakdown": dict(status_breakdown),
        "top_recommended_activities": top_recommended,
    }


def manager_guest_intelligence(db: Session, resort_id: int) -> dict[str, Any]:
    profiles = update_guest_segments(db, resort_id)

    since = datetime.utcnow() - timedelta(days=30)
    since_7d = datetime.utcnow() - timedelta(days=7)

    # ── Segment analytics ───────────────────────────────────────────────────
    segment_analytics = _build_segment_analytics(db, resort_id, profiles, since)

    # Legacy segment counts for training data banner
    segment_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for profile in profiles:
        group = "training_guest_count" if profile.is_training_sample else "guest_count"
        segment_counts[profile.segment][group] += 1

    # ── Activity interaction trends (14 days) ───────────────────────────────
    since_14d = datetime.utcnow() - timedelta(days=13)
    interactions = db.query(GuestActivityInteraction).filter(
        GuestActivityInteraction.resort_id == resort_id,
        GuestActivityInteraction.created_at >= since_14d,
    ).all()
    interaction_rows = [{
        "day": interaction.created_at.date().isoformat(),
        "interaction_type": interaction.interaction_type,
    } for interaction in interactions]
    if interaction_rows:
        trend = pd.DataFrame(interaction_rows).groupby(["day", "interaction_type"]).size().unstack(fill_value=0)
        trend = trend.reindex(pd.date_range(since_14d.date(), datetime.utcnow().date(), freq="D").strftime("%Y-%m-%d"), fill_value=0)
        activity_trends = [
            {"date": str(day), **{str(kind).lower(): int(count) for kind, count in row.items()}}
            for day, row in trend.iterrows()
        ]
    else:
        activity_trends = []

    training_interactions = db.query(GuestActivityInteraction).filter(
        GuestActivityInteraction.resort_id == resort_id,
        GuestActivityInteraction.created_at >= since_14d,
        GuestActivityInteraction.is_training_sample.is_(True),
    ).all()
    training_rows = [{
        "day": interaction.created_at.date().isoformat(),
        "interaction_type": interaction.interaction_type,
    } for interaction in training_interactions]
    training_activity_trends = []
    if training_rows:
        training_trend = pd.DataFrame(training_rows).groupby(["day", "interaction_type"]).size().unstack(fill_value=0)
        training_trend = training_trend.reindex(
            pd.date_range(since_14d.date(), datetime.utcnow().date(), freq="D").strftime("%Y-%m-%d"),
            fill_value=0,
        )
        training_activity_trends = [
            {"date": str(day), **{str(kind).lower(): int(count) for kind, count in row.items()}}
            for day, row in training_trend.iterrows()
        ]

    # ── Feedback / sentiment ─────────────────────────────────────────────────
    feedback_30d = db.query(GuestFeedback).filter(
        GuestFeedback.resort_id == resort_id,
        GuestFeedback.created_at >= since,
    ).all()
    feedback_7d = db.query(GuestFeedback).filter(
        GuestFeedback.resort_id == resort_id,
        GuestFeedback.created_at >= since_7d,
    ).all()
    training_feedback = [item for item in feedback_30d if item.is_training_sample]
    real_feedback_30d = [item for item in feedback_30d if not item.is_training_sample]

    topic_counts: Counter[str] = Counter(
        topic
        for item in real_feedback_30d if item.sentiment == "NEGATIVE"
        for topic in (item.topics or [])
    )
    sentiment_counts: Counter[str] = Counter(item.sentiment for item in real_feedback_30d)

    # All topics (positive + negative) for the topic breakdown
    all_topic_counts: Counter[str] = Counter(
        topic
        for item in real_feedback_30d
        for topic in (item.topics or [])
    )

    training_topic_counts: Counter[str] = Counter(
        topic
        for item in training_feedback if item.sentiment == "NEGATIVE"
        for topic in (item.topics or [])
    )

    # ── Average satisfaction (from all ratings) ──────────────────────────────
    all_ratings = db.query(GuestActivityInteraction).filter(
        GuestActivityInteraction.resort_id == resort_id,
        GuestActivityInteraction.interaction_type == "RATED",
        GuestActivityInteraction.rating.isnot(None),
    ).all()
    avg_satisfaction = round(float(np.mean([r.rating for r in all_ratings])), 2) if all_ratings else None

    # Training data summary
    training_data = {
        "profiles": db.query(GuestProfile).filter(GuestProfile.resort_id == resort_id).count(),
        "activities": db.query(ResortActivity).filter(ResortActivity.resort_id == resort_id).count(),
        "interactions": db.query(GuestActivityInteraction).filter(GuestActivityInteraction.resort_id == resort_id).count(),
        "feedback": db.query(GuestFeedback).filter(GuestFeedback.resort_id == resort_id).count(),
        "requests": db.query(GuestBookingRequest).filter(GuestBookingRequest.resort_id == resort_id).count(),
    }

    # ── Recommendation performance ───────────────────────────────────────────
    recommendation_performance = _build_recommendation_performance(db, resort_id)

    # ── Total activity interactions ──────────────────────────────────────────
    total_interactions_all = db.query(GuestActivityInteraction).filter(
        GuestActivityInteraction.resort_id == resort_id,
    ).count()

    return {
        "guest_count": len(profiles),
        "total_activity_interactions": total_interactions_all,
        "avg_satisfaction": avg_satisfaction,
        "feedback_7d_count": len(feedback_7d),
        # Rich behavioral segments
        "behavioral_segments": segment_analytics,
        # Legacy segments (for training data banner)
        "segments": [{"name": name, **dict(counts)} for name, counts in sorted(segment_counts.items())],
        # Activity trends
        "activity_trends": activity_trends,
        "training_activity_trends": training_activity_trends,
        # Feedback / sentiment
        "feedback": {
            "total": len(real_feedback_30d),
            "sentiment_counts": dict(sentiment_counts),
            "recurring_topics": [{"topic": topic, "count": count} for topic, count in topic_counts.most_common(8)],
            "all_topics": [{"topic": topic, "count": count} for topic, count in all_topic_counts.most_common(8)],
            "training_topics": [{"topic": topic, "count": count} for topic, count in training_topic_counts.most_common(8)],
        },
        # Recommendation engine performance
        "recommendation_performance": recommendation_performance,
        # Training data summary
        "training_data": training_data,
    }

