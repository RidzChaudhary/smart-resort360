from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Auth Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    resort_id: int
    department_id: Optional[int]
    name: str
    email: str
    role: str
    phone: Optional[str]
    avatar_url: Optional[str]

    class Config:
        from_attributes = True

# --- Recommendation Schemas ---
class RecommendationResponse(BaseModel):
    id: int
    resort_id: int
    type: str
    priority: str
    title: str
    recommended_action: str
    explanation: str
    expected_impact: str
    metrics_data: Optional[Dict[str, Any]] = None
    status: str
    modified_details: Optional[str] = None
    target_date: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class RecommendationActionRequest(BaseModel):
    action: str  # "APPROVE", "REJECT", "MODIFY"
    modified_quantity: Optional[float] = None
    modified_notes: Optional[str] = None
    assigned_department_id: Optional[int] = None

# --- Task Schemas ---
class TaskResponse(BaseModel):
    id: int
    resort_id: int
    recommendation_id: Optional[int]
    department_id: int
    department_name: Optional[str] = None
    assigned_to: Optional[int]
    assignee_name: Optional[str] = None
    title: str
    description: Optional[str]
    priority: str
    status: str
    due_date: Optional[datetime]
    sla_minutes: Optional[int] = None
    room_number: Optional[str]
    blocker_reason: Optional[str] = None
    escalated_to_user_id: Optional[int] = None
    escalated_at: Optional[datetime] = None
    is_overdue: bool = False
    minutes_overdue: int = 0
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    department_id: int
    assigned_to: Optional[int] = None
    title: str
    description: Optional[str] = None
    priority: Optional[str] = "MEDIUM"
    due_date: Optional[datetime] = None
    sla_minutes: Optional[int] = None
    room_number: Optional[str] = None

class TaskAssignRequest(BaseModel):
    assigned_to: int

class TaskStatusRequest(BaseModel):
    status: str  # PENDING, ASSIGNED, IN_PROGRESS, BLOCKED, ESCALATED, COMPLETED, CANCELLED
    blocker_reason: Optional[str] = None

class TaskEscalateRequest(BaseModel):
    blocker_reason: str
    escalate_to_user_id: Optional[int] = None

# --- Inventory & PO Schemas ---
class InventoryItemResponse(BaseModel):
    id: int
    resort_id: int
    name: str
    category: str
    unit: str
    current_stock: float
    reorder_threshold: float
    min_stock: float
    max_stock: float
    unit_cost: float
    consumption_rate_per_occupied_room: float
    lead_time_days: int
    stockout_risk: Optional[str] = "LOW"  # Computed dynamically: LOW, MEDIUM, HIGH, CRITICAL
    projected_days_left: Optional[float] = 0.0

    class Config:
        from_attributes = True

class PurchaseOrderResponse(BaseModel):
    id: int
    resort_id: int
    recommendation_id: Optional[int]
    inventory_item_id: int
    item_name: str
    quantity: float
    unit: str
    estimated_cost: float
    supplier: str
    status: str
    approved_by: Optional[str]
    created_at: datetime
    fulfilled_at: Optional[datetime]
    category: Optional[str] = None

    class Config:
        from_attributes = True

class PurchaseOrderCreate(BaseModel):
    inventory_item_id: int
    quantity: float
    supplier: Optional[str] = "Standard Vendor"

# --- Guest Request Schemas ---
class GuestRequestCreate(BaseModel):
    room_number: str
    guest_name: Optional[str] = "Guest"
    request_type: str
    description: str
    priority: Optional[str] = "MEDIUM"
    source: Optional[str] = "GUEST_PORTAL"

class InternalGuestRequestCreate(GuestRequestCreate):
    source: str = "FRONT_DESK"
    reported_by_user_id: Optional[int] = None

class RecommendationOutcomeCreate(BaseModel):
    actual_workload: Optional[float] = None
    actual_staff_used: Optional[int] = None
    completion_percentage: Optional[float] = None
    actual_completion_minutes: Optional[int] = None
    notes: Optional[str] = None

class GuestRequestResponse(BaseModel):
    id: int
    resort_id: int
    room_id: Optional[int]
    room_number: str
    guest_name: str
    request_type: str
    description: str
    priority: str
    status: str
    source: str  # GUEST_PORTAL, VERBAL_STAFF, FRONT_DESK, PHONE, EMAIL
    reported_by_user_id: Optional[int] = None
    task_id: Optional[int]
    assigned_to: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

# --- Activity Log Schemas ---
class ActivityLogResponse(BaseModel):
    id: int
    resort_id: int
    user_id: Optional[int]
    user_name: str
    user_role: str
    action_type: str
    entity_type: Optional[str]
    entity_id: Optional[int]
    description: str
    details_json: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True

# --- Forecast Schemas ---
class DayForecast(BaseModel):
    date: str
    day_name: str
    predicted_occupancy_pct: float  # Always ≤ 100%
    occupied_rooms: int  # Physical rooms occupied (capped at total_rooms)
    booking_demand_count: int  # Total bookings (can exceed capacity)
    overbooking_count: int  # Bookings beyond capacity
    total_rooms: int
    sellable_rooms: int = 0
    check_ins: int
    check_outs: int
    early_arrivals: int
    stay_overs: int
    cleaning_workload_rooms: int
    housekeepers_needed: int
    housekeepers_scheduled: int
    staffing_gap: int
    expected_revenue: float
    ml_confidence_score: float

class ForecastOverviewResponse(BaseModel):
    forecast_days: List[DayForecast]
    overall_summary: Dict[str, Any]
    model_metadata: Dict[str, Any]

    class Config:
        protected_namespaces = ()

# --- Room Schemas ---
class RoomResponse(BaseModel):
    id: int
    resort_id: int
    room_number: str
    room_type: str
    status: str
    floor: int
    max_guests: int

    class Config:
        from_attributes = True

class RoomStatusUpdateRequest(BaseModel):
    status: str  # clean, dirty, inspecting, maintenance, occupied


# --- Guest Intelligence Schemas ---
class GuestSessionRequest(BaseModel):
    room_number: str = Field(min_length=1, max_length=50)
    guest_name: str = Field(min_length=2, max_length=255)


class GuestLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=255)


class GuestServiceRequestCreate(BaseModel):
    request_type: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=5, max_length=2000)
    priority: str = "MEDIUM"


class ResortActivityCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=5, max_length=2000)
    category: str = Field(min_length=2, max_length=80)
    tags: List[str] = Field(default_factory=list, max_length=20)
    capacity: int = Field(gt=0, le=10000)
    available_slots: Optional[int] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    crowd_level: str = "MODERATE"


class ResortActivityUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=160)
    description: Optional[str] = Field(default=None, min_length=5, max_length=2000)
    category: Optional[str] = Field(default=None, min_length=2, max_length=80)
    tags: Optional[List[str]] = Field(default=None, max_length=20)
    capacity: Optional[int] = Field(default=None, gt=0, le=10000)
    available_slots: Optional[int] = Field(default=None, ge=0, le=10000)
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    crowd_level: Optional[str] = None
    active: Optional[bool] = None


class GuestActivityInteractionCreate(BaseModel):
    activity_id: int
    interaction_type: str
    rating: Optional[int] = Field(default=None, ge=1, le=5)


class GuestFeedbackCreate(BaseModel):
    comment: str = Field(min_length=5, max_length=2000)
    activity_id: Optional[int] = None


class GuestProfileResponse(BaseModel):
    total_stays: int
    total_nights: int
    average_party_size: float
    preferred_categories: List[str]
    preferred_tags: List[str]
    segment: str


class GuestRecommendationResponse(BaseModel):
    activity: Dict[str, Any]
    score: float
    reasons: List[str]
