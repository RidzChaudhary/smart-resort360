from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.connection import Base

# Phase 1 – import new models so they are registered with the same Base
from app.models.resort_event import ResortEvent        # noqa: F401 – registers table
from app.models.location import ResortLocation         # noqa: F401 – registers table
from app.models.weather_cache import WeatherCache      # noqa: F401 – registers table

class Resort(Base):
    __tablename__ = "resorts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    total_rooms = Column(Integer, default=100)
    address = Column(String(500), nullable=True)
    latitude = Column(Float, nullable=True)  # Geospatial coordinates
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    departments = relationship("Department", back_populates="resort", cascade="all, delete-orphan")
    rooms = relationship("Room", back_populates="resort", cascade="all, delete-orphan")
    users = relationship("User", back_populates="resort", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="resort", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="resort", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="resort", cascade="all, delete-orphan")
    inventory_items = relationship("InventoryItem", back_populates="resort", cascade="all, delete-orphan")
    purchase_orders = relationship("PurchaseOrder", back_populates="resort", cascade="all, delete-orphan")
    guest_requests = relationship("GuestRequest", back_populates="resort", cascade="all, delete-orphan")
    activity_logs = relationship("ActivityLog", back_populates="resort", cascade="all, delete-orphan")
    guest_profiles = relationship("GuestProfile", back_populates="resort", cascade="all, delete-orphan")
    resort_activities = relationship("ResortActivity", back_populates="resort", cascade="all, delete-orphan")
    guest_feedback = relationship("GuestFeedback", back_populates="resort", cascade="all, delete-orphan")
    guest_accounts = relationship("GuestAccount", back_populates="resort", cascade="all, delete-orphan")
    guest_booking_requests = relationship("GuestBookingRequest", back_populates="resort", cascade="all, delete-orphan")
    # Phase 1 relationships
    resort_events = relationship("ResortEvent", back_populates="resort", cascade="all, delete-orphan")
    resort_locations = relationship("ResortLocation", back_populates="resort", cascade="all, delete-orphan")


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    resort_id = Column(Integer, ForeignKey("resorts.id"), nullable=False)
    name = Column(String(100), nullable=False)  # Housekeeping, Front Desk, F&B, Maintenance
    created_at = Column(DateTime, default=datetime.utcnow)

    resort = relationship("Resort", back_populates="departments")
    users = relationship("User", back_populates="department")
    tasks = relationship("Task", back_populates="department")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    resort_id = Column(Integer, ForeignKey("resorts.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # MANAGER, FRONT_DESK, DEPARTMENT_HEAD, STAFF
    phone = Column(String(50), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    resort = relationship("Resort", back_populates="users")
    department = relationship("Department", back_populates="users")
    assigned_tasks = relationship("Task", back_populates="assignee", foreign_keys="Task.assigned_to")
    activity_logs = relationship("ActivityLog", back_populates="user")


class Room(Base):
    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    resort_id = Column(Integer, ForeignKey("resorts.id"), nullable=False)
    room_number = Column(String(50), nullable=False, index=True)
    room_type = Column(String(100), nullable=False)  # Standard, Deluxe, Suite, Ocean Villa
    status = Column(String(50), default="clean")  # clean, dirty, inspecting, maintenance, occupied
    floor = Column(Integer, default=1)
    max_guests = Column(Integer, default=2)
    created_at = Column(DateTime, default=datetime.utcnow)

    resort = relationship("Resort", back_populates="rooms")
    bookings = relationship("Booking", back_populates="room")
    guest_requests = relationship("GuestRequest", back_populates="room")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    resort_id = Column(Integer, ForeignKey("resorts.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    guest_name = Column(String(255), nullable=False)
    guest_email = Column(String(255), nullable=True)
    guest_phone = Column(String(50), nullable=True)
    check_in = Column(DateTime, nullable=False, index=True)
    check_out = Column(DateTime, nullable=False, index=True)
    status = Column(String(50), default="confirmed")  # confirmed, checked_in, checked_out, cancelled
    guests_count = Column(Integer, default=2)
    early_arrival = Column(Boolean, default=False)
    expected_arrival_time = Column(String(50), nullable=True)  # e.g., "10:00 AM"
    revenue = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    resort = relationship("Resort", back_populates="bookings")
    room = relationship("Room", back_populates="bookings")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    resort_id = Column(Integer, ForeignKey("resorts.id"), nullable=False)
    type = Column(String(50), nullable=False)  # staffing, inventory, maintenance
    priority = Column(String(50), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    title = Column(String(255), nullable=False)
    recommended_action = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    expected_impact = Column(Text, nullable=False)
    metrics_data = Column(JSON, nullable=True)
    status = Column(String(50), default="PENDING")  # PENDING, APPROVED, REJECTED, MODIFIED
    modified_details = Column(Text, nullable=True)
    target_date = Column(String(50), nullable=True)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    resort = relationship("Resort", back_populates="recommendations")
    tasks = relationship("Task", back_populates="recommendation")
    purchase_orders = relationship("PurchaseOrder", back_populates="recommendation")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    resort_id = Column(Integer, ForeignKey("resorts.id"), nullable=False)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(50), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(50), default="PENDING")  # PENDING, ASSIGNED, IN_PROGRESS, BLOCKED, ESCALATED, COMPLETED, CANCELLED
    due_date = Column(DateTime, nullable=True)
    sla_minutes = Column(Integer, nullable=True)  # Expected completion time in minutes
    room_number = Column(String(50), nullable=True)

    # Escalation fields
    blocker_reason = Column(Text, nullable=True)
    escalated_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    escalated_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    resort = relationship("Resort", back_populates="tasks")
    recommendation = relationship("Recommendation", back_populates="tasks")
    department = relationship("Department", back_populates="tasks")
    assignee = relationship("User", back_populates="assigned_tasks", foreign_keys=[assigned_to])
    escalated_to_user = relationship("User", foreign_keys=[escalated_to_user_id])
    guest_requests = relationship("GuestRequest", back_populates="task")

    @property
    def is_overdue(self):
        """Check if task is overdue based on due_date."""
        if not self.due_date or self.status in ['COMPLETED', 'CANCELLED']:
            return False
        return datetime.utcnow() > self.due_date

    @property
    def minutes_overdue(self):
        """Calculate how many minutes the task is overdue."""
        if not self.is_overdue:
            return 0
        delta = datetime.utcnow() - self.due_date
        return int(delta.total_seconds() / 60)


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    resort_id = Column(Integer, ForeignKey("resorts.id"), nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), default="General")  # F&B, Housekeeping, Guest Amenities, Maintenance
    unit = Column(String(50), nullable=False)  # kg, liters, sets, units, bottles
    current_stock = Column(Float, default=0.0)
    reorder_threshold = Column(Float, default=10.0)
    min_stock = Column(Float, default=5.0)
    max_stock = Column(Float, default=100.0)
    unit_cost = Column(Float, default=0.0)
    consumption_rate_per_occupied_room = Column(Float, default=0.0)
    lead_time_days = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    resort = relationship("Resort", back_populates="inventory_items")
    purchase_orders = relationship("PurchaseOrder", back_populates="inventory_item")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    resort_id = Column(Integer, ForeignKey("resorts.id"), nullable=False)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=True)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    item_name = Column(String(255), nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    estimated_cost = Column(Float, default=0.0)
    supplier = Column(String(255), default="Standard Vendor")
    status = Column(String(50), default="PENDING")  # PENDING, ORDERED, RECEIVED, CANCELLED
    approved_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    fulfilled_at = Column(DateTime, nullable=True)

    resort = relationship("Resort", back_populates="purchase_orders")
    recommendation = relationship("Recommendation", back_populates="purchase_orders")
    inventory_item = relationship("InventoryItem", back_populates="purchase_orders")


class GuestRequest(Base):
    __tablename__ = "guest_requests"

    id = Column(Integer, primary_key=True, index=True)
    resort_id = Column(Integer, ForeignKey("resorts.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=True)
    room_number = Column(String(50), nullable=False)
    guest_name = Column(String(255), default="Guest")
    request_type = Column(String(100), nullable=False)  # AC/Maintenance, Housekeeping/Towels, F&B/Room Service, Luggage, Amenities, Other
    description = Column(Text, nullable=False)
    priority = Column(String(50), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(50), default="PENDING")  # PENDING, IN_PROGRESS, COMPLETED, CANCELLED
    is_training_sample = Column(Boolean, default=False, nullable=False)

    # Source tracking
    source = Column(String(50), default="GUEST_PORTAL")  # GUEST_PORTAL, VERBAL_STAFF, FRONT_DESK, PHONE, EMAIL
    reported_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    assigned_to = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    resort = relationship("Resort", back_populates="guest_requests")
    room = relationship("Room", back_populates="guest_requests")
    task = relationship("Task", back_populates="guest_requests")
    reported_by_user = relationship("User", foreign_keys=[reported_by_user_id])


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    resort_id = Column(Integer, ForeignKey("resorts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_name = Column(String(255), default="System")
    user_role = Column(String(50), default="SYSTEM")
    action_type = Column(String(100), nullable=False)  # RECOMMENDATION_APPROVED, TASK_ASSIGNED, TASK_COMPLETED, PO_CREATED, GUEST_REQUEST, SYSTEM_RESET, etc.
    entity_type = Column(String(100), nullable=True)  # recommendation, task, purchase_order, guest_request
    entity_id = Column(Integer, nullable=True)
    description = Column(Text, nullable=False)
    details_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    resort = relationship("Resort", back_populates="activity_logs")
    user = relationship("User", back_populates="activity_logs")


class GuestProfile(Base):
    __tablename__ = "guest_profiles"
    __table_args__ = (UniqueConstraint("resort_id", "guest_key", name="uq_guest_profile_resort_key"),)

    id = Column(Integer, primary_key=True, index=True)
    resort_id = Column(Integer, ForeignKey("resorts.id"), nullable=False, index=True)
    guest_key = Column(String(64), nullable=False, index=True)
    total_stays = Column(Integer, default=0, nullable=False)
    total_nights = Column(Integer, default=0, nullable=False)
    average_party_size = Column(Float, default=1.0, nullable=False)
    preferred_categories = Column(JSON, default=list, nullable=False)
    preferred_tags = Column(JSON, default=list, nullable=False)
    segment = Column(String(50), default="New Guest", nullable=False)
    is_training_sample = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    resort = relationship("Resort", back_populates="guest_profiles")
    interactions = relationship("GuestActivityInteraction", back_populates="guest_profile", cascade="all, delete-orphan")
    feedback = relationship("GuestFeedback", back_populates="guest_profile", cascade="all, delete-orphan")


class ResortActivity(Base):
    __tablename__ = "resort_activities"

    id = Column(Integer, primary_key=True, index=True)
    resort_id = Column(Integer, ForeignKey("resorts.id"), nullable=False, index=True)
    name = Column(String(160), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(80), nullable=False, index=True)
    tags = Column(JSON, default=list, nullable=False)
    capacity = Column(Integer, nullable=False)
    available_slots = Column(Integer, nullable=False)
    start_at = Column(DateTime, nullable=True)
    end_at = Column(DateTime, nullable=True)
    crowd_level = Column(String(20), default="MODERATE", nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    is_training_sample = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    resort = relationship("Resort", back_populates="resort_activities")
    interactions = relationship("GuestActivityInteraction", back_populates="activity", cascade="all, delete-orphan")


class GuestActivityInteraction(Base):
    __tablename__ = "guest_activity_interactions"

    id = Column(Integer, primary_key=True, index=True)
    resort_id = Column(Integer, ForeignKey("resorts.id"), nullable=False, index=True)
    guest_profile_id = Column(Integer, ForeignKey("guest_profiles.id"), nullable=False, index=True)
    activity_id = Column(Integer, ForeignKey("resort_activities.id"), nullable=False, index=True)
    interaction_type = Column(String(20), nullable=False, index=True)
    rating = Column(Integer, nullable=True)
    is_training_sample = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    guest_profile = relationship("GuestProfile", back_populates="interactions")
    activity = relationship("ResortActivity", back_populates="interactions")


class GuestFeedback(Base):
    __tablename__ = "guest_feedback"

    id = Column(Integer, primary_key=True, index=True)
    resort_id = Column(Integer, ForeignKey("resorts.id"), nullable=False, index=True)
    guest_profile_id = Column(Integer, ForeignKey("guest_profiles.id"), nullable=False, index=True)
    activity_id = Column(Integer, ForeignKey("resort_activities.id"), nullable=True, index=True)
    comment = Column(Text, nullable=False)
    sentiment = Column(String(20), nullable=False, index=True)
    topics = Column(JSON, default=list, nullable=False)
    is_training_sample = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    resort = relationship("Resort", back_populates="guest_feedback")
    guest_profile = relationship("GuestProfile", back_populates="feedback")
    activity = relationship("ResortActivity")


class GuestAccount(Base):
    __tablename__ = "guest_accounts"
    __table_args__ = (UniqueConstraint("booking_id", name="uq_guest_account_booking"),)

    id = Column(Integer, primary_key=True, index=True)
    resort_id = Column(Integer, ForeignKey("resorts.id"), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    resort = relationship("Resort", back_populates="guest_accounts")
    booking = relationship("Booking")


class GuestBookingRequest(Base):
    __tablename__ = "guest_booking_requests"
    __table_args__ = (UniqueConstraint("booking_id", "guest_request_id", name="uq_guest_booking_request"),)

    id = Column(Integer, primary_key=True, index=True)
    resort_id = Column(Integer, ForeignKey("resorts.id"), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, index=True)
    guest_request_id = Column(Integer, ForeignKey("guest_requests.id"), nullable=False, index=True)
    is_training_sample = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    resort = relationship("Resort", back_populates="guest_booking_requests")
    booking = relationship("Booking")
    guest_request = relationship("GuestRequest")

