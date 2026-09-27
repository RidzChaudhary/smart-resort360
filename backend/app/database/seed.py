import sys
import os
import random
import argparse
from datetime import datetime, timedelta
import bcrypt
from sqlalchemy.orm import Session

from app.database.connection import Base, engine, SessionLocal
from app.models import (
    Resort, Department, User, Room, Booking,
    InventoryItem, Recommendation, Task, PurchaseOrder,
    GuestRequest, ActivityLog
)
from app.services.forecast_engine import ForecastEngine
from app.services.guest_training_data import seed_guest_training_data
from app.services.recommendation_engine import RecommendationEngine

def get_password_hash(password: str) -> str:
    if os.getenv("APP_ENV", "development").strip().casefold() == "production":
        variable = "GUEST_DEMO_PASSWORD" if password == "guest123" else "DEMO_ACCOUNT_PASSWORD"
        password = os.getenv(variable, "")
        if len(password) < 16:
            raise RuntimeError(f"{variable} must be configured with at least 16 characters before production seeding")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def seed_database(reset_schema: bool = False):
    """Seed an empty database, or explicitly reset a development database."""
    app_env = os.getenv("APP_ENV", "development").strip().casefold()
    if reset_schema and app_env == "production":
        raise RuntimeError("Destructive database reset is disabled in production")
    if reset_schema:
        print("Resetting development database schema...")
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()

    try:
        if not reset_schema and db.query(Resort).first():
            print("Database already contains a resort; safe seed skipped without changing existing data.")
            return {"skipped": True}

        print("🏨 Creating Resort...")
        resort = Resort(
            name="Azure Palm Resort",
            total_rooms=120,
            address="Calangute Beach Road, Goa, India 403516",
            latitude=15.2993,
            longitude=73.9876
        )
        db.add(resort)
        db.flush()

        print("🏢 Creating Departments...")
        depts = [
            Department(resort_id=resort.id, name="Housekeeping"),
            Department(resort_id=resort.id, name="Front Desk"),
            Department(resort_id=resort.id, name="Food & Beverage"),
            Department(resort_id=resort.id, name="Maintenance"),
            Department(resort_id=resort.id, name="Inventory"),
        ]
        db.add_all(depts)
        db.flush()

        hk_dept = depts[0]
        fd_dept = depts[1]
        fb_dept = depts[2]
        maint_dept = depts[3]
        inventory_dept = depts[4]

        print("👥 Creating Users across all 4 roles...")
        users = [
            # 1. Manager
            User(
                resort_id=resort.id,
                department_id=None,
                name="Sarah Jenkins",
                email="manager@resort360.com",
                password_hash=get_password_hash("password123"),
                role="MANAGER",
                phone="+1 (555) 234-5678",
                avatar_url="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150"
            ),
            # 2. Front Desk Lead & Staff
            User(
                resort_id=resort.id,
                department_id=fd_dept.id,
                name="Alex Rivera",
                email="frontdesk@resort360.com",
                password_hash=get_password_hash("password123"),
                role="FRONT_DESK",
                phone="+1 (555) 345-6789",
                avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150"
            ),
            # 3. Department Heads
            User(
                resort_id=resort.id,
                department_id=hk_dept.id,
                name="Maria Santos",
                email="housekeeping.head@resort360.com",
                password_hash=get_password_hash("password123"),
                role="DEPARTMENT_HEAD",
                phone="+1 (555) 456-7890",
                avatar_url="https://images.unsplash.com/photo-1580489944761-15a19d654956?w=150"
            ),
            User(
                resort_id=resort.id,
                department_id=fb_dept.id,
                name="Chef Marco Rossi",
                email="fb.head@resort360.com",
                password_hash=get_password_hash("password123"),
                role="DEPARTMENT_HEAD",
                phone="+1 (555) 567-8901",
                avatar_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150"
            ),
            User(
                resort_id=resort.id,
                department_id=maint_dept.id,
                name="David Chen",
                email="maintenance.head@resort360.com",
                password_hash=get_password_hash("password123"),
                role="DEPARTMENT_HEAD",
                phone="+1 (555) 678-9012",
                avatar_url="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150"
            ),
            # 4. Staff members
            User(
                resort_id=resort.id,
                department_id=hk_dept.id,
                name="Elena Rostova",
                email="staff.elena@resort360.com",
                password_hash=get_password_hash("password123"),
                role="STAFF",
                phone="+1 (555) 789-0123",
                avatar_url="https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150"
            ),
            User(
                resort_id=resort.id,
                department_id=hk_dept.id,
                name="Carlos Mendez",
                email="staff.carlos@resort360.com",
                password_hash=get_password_hash("password123"),
                role="STAFF",
                phone="+1 (555) 890-1234",
                avatar_url="https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=150"
            ),
            User(
                resort_id=resort.id,
                department_id=hk_dept.id,
                name="Amina Diallo",
                email="staff.amina@resort360.com",
                password_hash=get_password_hash("password123"),
                role="STAFF",
                phone="+1 (555) 890-1235",
                avatar_url="https://images.unsplash.com/photo-1531746020798-e6953c6e8e04?w=150"
            ),
            User(
                resort_id=resort.id,
                department_id=maint_dept.id,
                name="Jamal Washington",
                email="staff.jamal@resort360.com",
                password_hash=get_password_hash("password123"),
                role="STAFF",
                phone="+1 (555) 901-2345",
                avatar_url="https://images.unsplash.com/photo-1522075469751-3a6694fb2f61?w=150"
            ),
            User(
                resort_id=resort.id,
                department_id=fb_dept.id,
                name="Priya Sharma",
                email="staff.priya@resort360.com",
                password_hash=get_password_hash("password123"),
                role="STAFF",
                phone="+1 (555) 012-3456",
                avatar_url="https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150"
            ),
            User(
                resort_id=resort.id,
                department_id=inventory_dept.id,
                name="Nina Patel",
                email="inventory.head@resort360.com",
                password_hash=get_password_hash("password123"),
                role="DEPARTMENT_HEAD",
                phone="+1 (555) 012-3457",
                avatar_url="https://images.unsplash.com/photo-1551836022-d5d88e9218df?w=150"
            ),
            User(
                resort_id=resort.id,
                department_id=inventory_dept.id,
                name="Leo Martin",
                email="staff.leo@resort360.com",
                password_hash=get_password_hash("password123"),
                role="STAFF",
                phone="+1 (555) 012-3458",
                avatar_url="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150"
            ),
            User(
                resort_id=resort.id,
                department_id=fb_dept.id,
                name="Maya Brooks",
                email="staff.maya@resort360.com",
                password_hash=get_password_hash("password123"),
                role="STAFF",
                phone="+1 (555) 012-3460",
                avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150"
            ),
            User(
                resort_id=resort.id,
                department_id=fb_dept.id,
                name="Rafael Torres",
                email="staff.rafael@resort360.com",
                password_hash=get_password_hash("password123"),
                role="STAFF",
                phone="+1 (555) 012-3461",
                avatar_url="https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150"
            ),
            User(
                resort_id=resort.id,
                department_id=inventory_dept.id,
                name="Grace Kim",
                email="staff.grace@resort360.com",
                password_hash=get_password_hash("password123"),
                role="STAFF",
                phone="+1 (555) 012-3462",
                avatar_url="https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150"
            ),
            User(
                resort_id=resort.id,
                department_id=inventory_dept.id,
                name="Omar Said",
                email="staff.omar@resort360.com",
                password_hash=get_password_hash("password123"),
                role="STAFF",
                phone="+1 (555) 012-3463",
                avatar_url="https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=150"
            ),
        ]
        db.add_all(users)
        db.flush()

        print("🛏️ Creating 120 Resort Rooms across 4 floors (70 Standard, 30 Deluxe, 15 Suite, 5 Villa)...")
        rooms = []
        statuses = ["clean", "clean", "dirty", "occupied", "occupied", "occupied", "inspecting"]

        # Exact room distribution as specified:
        # Standard: 70 rooms (Room 101-125, 201-225, 301-320)
        # Deluxe: 30 rooms (Room 321-325, 401-425)
        # Suite: 15 rooms (Room 501-515)
        # Villa: 5 rooms (Villa 601-605)
        
        room_specs = []
        for r in range(101, 126): room_specs.append((r, "Standard", 1, 2))
        for r in range(201, 226): room_specs.append((r, "Standard", 2, 2))
        for r in range(301, 321): room_specs.append((r, "Standard", 3, 2))
        for r in range(321, 326): room_specs.append((r, "Deluxe", 3, 3))
        for r in range(401, 426): room_specs.append((r, "Deluxe", 4, 3))
        for r in range(501, 516): room_specs.append((r, "Suite", 5, 4))
        for r in range(601, 606): room_specs.append((r, "Villa", 6, 6))

        for idx, (r_num, r_type, fl, max_g) in enumerate(room_specs):
            status = random.choice(statuses)
            if idx % 10 in (0, 1):
                status = "dirty"
            elif idx % 10 == 2:
                status = "inspecting"
            elif idx % 20 == 5:
                status = "maintenance"

            room = Room(
                resort_id=resort.id,
                room_number=str(r_num),
                room_type=r_type,
                status=status,
                floor=fl,
                max_guests=max_g
            )
            rooms.append(room)

        db.add_all(rooms)
        db.flush()

        print("📦 Creating Inventory Items...")
        inventory = [
            InventoryItem(
                resort_id=resort.id,
                name="Fresh Farm Eggs",
                category="F&B",
                unit="cartons (30 eggs)",
                current_stock=18.0,
                reorder_threshold=50.0,
                min_stock=20.0,
                max_stock=120.0,
                unit_cost=8.50,
                consumption_rate_per_occupied_room=0.35,  # ~10 eggs / room breakfast
                lead_time_days=2
            ),
            InventoryItem(
                resort_id=resort.id,
                name="Organic Whole Milk",
                category="F&B",
                unit="liters",
                current_stock=32.0,
                reorder_threshold=60.0,
                min_stock=25.0,
                max_stock=150.0,
                unit_cost=3.20,
                consumption_rate_per_occupied_room=0.45,
                lead_time_days=1
            ),
            InventoryItem(
                resort_id=resort.id,
                name="Egyptian Cotton Linen Sets",
                category="Housekeeping",
                unit="sets",
                current_stock=42.0,
                reorder_threshold=90.0,
                min_stock=40.0,
                max_stock=200.0,
                unit_cost=45.00,
                consumption_rate_per_occupied_room=0.60,
                lead_time_days=3
            ),
            InventoryItem(
                resort_id=resort.id,
                name="Plush Bath Towel Bundles",
                category="Housekeeping",
                unit="bundles (4 towels)",
                current_stock=65.0,
                reorder_threshold=110.0,
                min_stock=50.0,
                max_stock=250.0,
                unit_cost=22.00,
                consumption_rate_per_occupied_room=0.85,
                lead_time_days=2
            ),
            InventoryItem(
                resort_id=resort.id,
                name="Luxury Spa Shampoo (300ml)",
                category="Guest Amenities",
                unit="bottles",
                current_stock=280.0,
                reorder_threshold=150.0,
                min_stock=80.0,
                max_stock=500.0,
                unit_cost=4.80,
                consumption_rate_per_occupied_room=0.70,
                lead_time_days=4
            ),
            InventoryItem(
                resort_id=resort.id,
                name="HVAC Air Filter Units",
                category="Maintenance",
                unit="filters",
                current_stock=8.0,
                reorder_threshold=15.0,
                min_stock=10.0,
                max_stock=40.0,
                unit_cost=18.50,
                consumption_rate_per_occupied_room=0.05,
                lead_time_days=2
            ),
        ]
        db.add_all(inventory)
        db.flush()

        print("📅 Creating Realistic Synthetic Bookings (~250 bookings)...")
        guest_names = [
            "Rahul Mehta", "Priya Nair", "Arjun Kapoor", "Ananya Shah",
            "Vikram Malhotra", "Kavita Sharma", "Devendra Patel", "Meera Reddy",
            "Rohan Joshi", "Sneha Verma", "Siddharth Malhotra", "Neha Gupta",
            "Aditya Sharma", "Ritu Singhania", "Manish Rao", "Deepa Iyer",
            "Rajesh Kulkarni", "Sunita Deshmukh", "Alok Verma", "Pooja Hegde",
            "Tarun Banerjee", "Shweta Agarwal", "Amit Trivedi", "Divya Saxena",
            "Rohit Sharma", "Priyanka Chopra", "Karan Johar", "Natasha Poonawalla"
        ]

        today = datetime.utcnow().replace(hour=14, minute=0, second=0, microsecond=0)
        bookings = []

        # 1. Historical Bookings (Past 60 days) - for ML linear regression training
        for day_offset in range(-60, 0):
            b_date = today + timedelta(days=day_offset)
            # Create weekend peaks
            is_weekend = b_date.weekday() >= 5
            day_bookings_count = random.randint(18, 25) if is_weekend else random.randint(10, 16)

            for _ in range(day_bookings_count):
                room = random.choice(rooms)
                stay_nights = random.randint(2, 5)
                check_in_dt = b_date
                check_out_dt = check_in_dt + timedelta(days=stay_nights)

                booking = Booking(
                    resort_id=resort.id,
                    room_id=room.id,
                    guest_name=random.choice(guest_names),
                    guest_email="guest@example.com",
                    guest_phone="+1 555-0199",
                    check_in=check_in_dt,
                    check_out=check_out_dt,
                    status="checked_out" if check_out_dt < today else "checked_in",
                    guests_count=random.randint(1, 4),
                    early_arrival=random.random() < 0.20,
                    revenue=stay_nights * random.choice([160, 220, 350, 600])
                )
                bookings.append(booking)

        # 2. TODAY's Active Stays (already checked in from previous days)
        for r_idx in range(50):
            room = rooms[r_idx]
            check_in_dt = today - timedelta(days=random.randint(1, 3))
            check_out_dt = today + timedelta(days=random.randint(1, 4))
            booking = Booking(
                resort_id=resort.id,
                room_id=room.id,
                guest_name=random.choice(guest_names),
                guest_email=f"guest{r_idx}@example.com",
                check_in=check_in_dt,
                check_out=check_out_dt,
                status="checked_in",
                guests_count=random.randint(1, 4),
                early_arrival=False,
                revenue=450.0
            )
            bookings.append(booking)

        # TODAY's Check-ins (arriving today) - 15 arrivals
        for r_idx in range(50, 65):
            room = rooms[r_idx]
            check_in_dt = today
            check_out_dt = today + timedelta(days=random.randint(2, 5))
            is_early = (r_idx < 53)  # 3 early arrivals

            booking = Booking(
                resort_id=resort.id,
                room_id=room.id,
                guest_name=random.choice(guest_names) + f" (Today Arrival {r_idx-49})",
                guest_email=f"today_arrival{r_idx-49}@example.com",
                check_in=check_in_dt,
                check_out=check_out_dt,
                status="confirmed",
                guests_count=random.randint(1, 4),
                early_arrival=is_early,
                expected_arrival_time="10:00 AM" if is_early else "03:00 PM",
                revenue=random.choice([180, 250, 420, 650])
            )
            bookings.append(booking)

        # TODAY's Check-outs (departing today) - 12 departures
        for r_idx in range(65, 77):
            room = rooms[r_idx]
            check_in_dt = today - timedelta(days=random.randint(2, 4))
            check_out_dt = today
            booking = Booking(
                resort_id=resort.id,
                room_id=room.id,
                guest_name=random.choice(guest_names) + f" (Today Departure {r_idx-64})",
                guest_email=f"today_departure{r_idx-64}@example.com",
                check_in=check_in_dt,
                check_out=check_out_dt,
                status="checked_in",
                guests_count=random.randint(1, 3),
                early_arrival=False,
                revenue=random.choice([320, 480, 720])
            )
            bookings.append(booking)

        # 3. TOMORROW (The Core Operational Spike Scenario)
        # 68 check-ins, 31 check-outs, 18 early arrivals -> 95% occupancy!
        tomorrow = today + timedelta(days=1)
        for r_idx in range(68):
            room = rooms[r_idx]
            check_in_dt = tomorrow
            check_out_dt = tomorrow + timedelta(days=random.randint(2, 5))
            is_early = (r_idx < 18)  # 18 early arrivals!

            booking = Booking(
                resort_id=resort.id,
                room_id=room.id,
                guest_name=random.choice(guest_names) + f" ({r_idx+1})",
                guest_email=f"arrival{r_idx+1}@example.com",
                check_in=check_in_dt,
                check_out=check_out_dt,
                status="confirmed",
                guests_count=random.randint(1, 4),
                early_arrival=is_early,
                expected_arrival_time="10:30 AM" if is_early else "03:00 PM",
                revenue=random.choice([180, 250, 420, 850])
            )
            bookings.append(booking)

        # 31 check-outs tomorrow
        for r_idx in range(31):
            room = rooms[r_idx + 10]
            check_in_dt = today - timedelta(days=2)
            check_out_dt = tomorrow
            booking = Booking(
                resort_id=resort.id,
                room_id=room.id,
                guest_name=random.choice(guest_names) + f" (Departing {r_idx+1})",
                guest_email=f"checkout{r_idx+1}@example.com",
                check_in=check_in_dt,
                check_out=check_out_dt,
                status="checked_in",
                guests_count=2,
                early_arrival=False,
                revenue=360.0
            )
            bookings.append(booking)

        # 4. Next 6 Days Future Bookings
        for day_f in range(2, 8):
            f_date = today + timedelta(days=day_f)
            count = random.randint(40, 75)
            for f_i in range(count):
                room = rooms[f_i % len(rooms)]
                booking = Booking(
                    resort_id=resort.id,
                    room_id=room.id,
                    guest_name=random.choice(guest_names),
                    guest_email=f"future{day_f}_{f_i}@example.com",
                    check_in=f_date,
                    check_out=f_date + timedelta(days=random.randint(2, 4)),
                    status="confirmed",
                    guests_count=random.randint(1, 3),
                    early_arrival=random.random() < 0.15,
                    revenue=random.choice([190, 240, 380])
                )
                bookings.append(booking)

        db.add_all(bookings)
        db.flush()

        print("🛎️ Creating Realistic Guest Requests...")
        guest_reqs = [
            GuestRequest(
                resort_id=resort.id,
                room_id=rooms[3].id,
                room_number="104",
                guest_name="Emily Watson",
                request_type="Housekeeping/Towels",
                description="Requested 3 extra pool towels and plush bathrobes for children.",
                priority="MEDIUM",
                status="IN_PROGRESS",
                assigned_to="Elena Rostova"
            ),
            GuestRequest(
                resort_id=resort.id,
                room_id=rooms[8].id,
                room_number="109",
                guest_name="Marcus Sterling",
                request_type="AC/Maintenance",
                description="Air conditioning unit is blowing lukewarm air. Room temperature is 78°F.",
                priority="HIGH",
                status="PENDING",
                assigned_to="Jamal Washington"
            ),
            GuestRequest(
                resort_id=resort.id,
                room_id=rooms[26].id,
                room_number="202",
                guest_name="Chloe Dubois",
                request_type="F&B/Room Service",
                description="Breakfast hamper delivery requested for 7:30 AM tomorrow with almond milk.",
                priority="LOW",
                status="PENDING"
            ),
        ]
        db.add_all(guest_reqs)
        db.flush()

        print("📋 Creating Initial Department Tasks...")
        tasks = [
            Task(
                resort_id=resort.id,
                department_id=maint_dept.id,
                assigned_to=users[8].id,  # Jamal
                title="Inspect HVAC Unit Room 109",
                description="Guest reported weak cooling. Check compressor and refrigerant pressure.",
                priority="HIGH",
                status="IN_PROGRESS",
                room_number="109",
                due_date=datetime.utcnow() + timedelta(hours=2)
            ),
            Task(
                resort_id=resort.id,
                department_id=hk_dept.id,
                assigned_to=users[5].id,  # Elena
                title="Deliver Extra Linens & Towels to Room 104",
                description="Pool towels and bathrobes delivery.",
                priority="MEDIUM",
                status="IN_PROGRESS",
                room_number="104",
                due_date=datetime.utcnow() + timedelta(hours=1)
            ),
            Task(
                resort_id=resort.id,
                department_id=hk_dept.id,
                assigned_to=users[6].id,  # Carlos
                title="Deep Clean & Sanitize Villa 401",
                description="VIP Arrival scheduled for tomorrow 11:00 AM.",
                priority="HIGH",
                status="PENDING",
                room_number="401",
                due_date=datetime.utcnow() + timedelta(hours=6)
            ),
            Task(
                resort_id=resort.id,
                department_id=hk_dept.id,
                title="Refresh High-Turnover Room 215",
                description="Prepare room 215 for the next arrival. The housekeeping SLA has already been missed and requires department-head assignment.",
                priority="HIGH",
                status="PENDING",
                room_number="215",
                due_date=datetime.utcnow() - timedelta(minutes=45),
                sla_minutes=120
            ),
            Task(
                resort_id=resort.id,
                department_id=fb_dept.id,
                assigned_to=users[9].id,
                title="Prepare breakfast service forecast",
                description="Review tomorrow's guest count and confirm breakfast station staffing.",
                priority="MEDIUM",
                status="ASSIGNED",
                due_date=datetime.utcnow() + timedelta(hours=5),
                sla_minutes=300,
            ),
            Task(
                resort_id=resort.id,
                department_id=fb_dept.id,
                title="Confirm allergy-safe buffet labels",
                description="Review dietary notes for tomorrow's arrivals and confirm buffet labels with the kitchen team.",
                priority="HIGH",
                status="PENDING",
                due_date=datetime.utcnow() + timedelta(hours=2),
                sla_minutes=120,
            ),
            Task(
                resort_id=resort.id,
                department_id=fb_dept.id,
                assigned_to=users[9].id,
                title="Review pool bar stock before evening service",
                description="Check beverage counts against the evening service forecast and flag low items.",
                priority="MEDIUM",
                status="IN_PROGRESS",
                due_date=datetime.utcnow() + timedelta(hours=3),
                sla_minutes=240,
            ),
            Task(
                resort_id=resort.id,
                department_id=fb_dept.id,
                assigned_to=users[9].id,
                title="Resolve beverage cooler temperature alert",
                description="Verify product temperature and coordinate the cooler inspection before the next service.",
                priority="HIGH",
                status="BLOCKED",
                due_date=datetime.utcnow() - timedelta(minutes=20),
                sla_minutes=60,
                blocker_reason="Temperature remains above target; cooler inspection is pending.",
            ),
            Task(
                resort_id=resort.id,
                department_id=inventory_dept.id,
                assigned_to=users[11].id,
                title="Reconcile low-stock linen inventory",
                description="Verify linen counts and prepare the replenishment request for housekeeping supplies.",
                priority="HIGH",
                status="ASSIGNED",
                due_date=datetime.utcnow() + timedelta(hours=3),
                sla_minutes=180,
            ),
        ]
        db.add_all(tasks)
        db.flush()

        print("🤖 Running AI Recommendation Engine to generate initial explainable recommendations...")
        rec_engine = RecommendationEngine(db, resort.id)
        rec_engine.generate_and_sync_recommendations()

        print("📜 Creating Initial Activity Logs...")
        logs = [
            ActivityLog(
                resort_id=resort.id,
                user_id=users[0].id,
                user_name="Sarah Jenkins",
                user_role="MANAGER",
                action_type="SYSTEM_INITIALIZED",
                entity_type="system",
                description="Smart Resort 360 initialized Azure Haven operations database.",
                created_at=datetime.utcnow() - timedelta(hours=4)
            ),
            ActivityLog(
                resort_id=resort.id,
                user_name="AI Predictive Engine",
                user_role="SYSTEM",
                action_type="RISK_DETECTED",
                entity_type="recommendation",
                description="AI detected tomorrow's 95% occupancy surge (68 check-ins, 31 check-outs, 18 early arrivals). Generated housekeeping staffing recommendation.",
                created_at=datetime.utcnow() - timedelta(hours=2)
            ),
            ActivityLog(
                resort_id=resort.id,
                user_name="AI Predictive Engine",
                user_role="SYSTEM",
                action_type="STOCKOUT_RISK_DETECTED",
                entity_type="inventory",
                description="AI detected F&B stockout risk for Fresh Farm Eggs and Egyptian Cotton Linen Sets based on projected 7-day occupancy.",
                created_at=datetime.utcnow() - timedelta(hours=1)
            ),
        ]
        db.add_all(logs)
        guest_training_summary = seed_guest_training_data(db, resort.id)
        db.commit()

        print("✅ Database seeding complete! Summary:")
        print(f"   • Resort: {resort.name}")
        print(f"   • Rooms: {len(rooms)}")
        print(f"   • Users: {len(users)}")
        print(f"   • Bookings: {len(bookings)}")
        print(f"   • Inventory Items: {len(inventory)}")
        print(f"   • Guest Intelligence Training Data: {guest_training_summary}")
        if app_env == "production":
            print("   • Demo accounts use the configured deployment passwords.")
        else:
            print("   • Default Credentials:")
            print("     - Manager: manager@resort360.com / password123")
            print("     - Front Desk: frontdesk@resort360.com / password123")
            print("     - Housekeeping Lead: housekeeping.head@resort360.com / password123")
            print("     - Maintenance Lead: maintenance.head@resort360.com / password123")
            print("     - Food & Beverage Lead: fb.head@resort360.com / password123")
            print("     - Inventory Lead: inventory.head@resort360.com / password123")
            print("     - Guest Demo: guest.demo@resort360.com / guest123")
            print("     - Staff: staff.elena@resort360.com / password123")
        return {"skipped": False, "resort_id": resort.id, "users": len(users), "bookings": len(bookings)}

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize or reset Smart Resort 360 synthetic data.")
    parser.add_argument("--reset", action="store_true", help="Destructively reset a development database.")
    args = parser.parse_args()
    seed_database(reset_schema=args.reset)
