import unittest
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.connection import Base, get_db
from app.models import (
    ActivityLog,
    Booking,
    Department,
    GuestAccount,
    GuestActivityInteraction,
    GuestProfile,
    InventoryItem,
    PurchaseOrder,
    Recommendation,
    Resort,
    Room,
    Task,
    User,
)
from app.routes.guest_intelligence import router
from app.routes.recommendations import router as recommendations_router
from app.services.guest_intelligence import get_or_create_guest_profile
from app.services.guest_training_data import seed_guest_training_data
from app.utils.auth import create_access_token, get_password_hash


class GuestIntelligenceApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.Session()

        resort = Resort(name="Test Resort", total_rooms=5)
        self.db.add(resort)
        self.db.flush()
        room = Room(resort_id=resort.id, room_number="A12", room_type="Suite")
        department = Department(resort_id=resort.id, name="Housekeeping")
        manager = User(
            resort_id=resort.id,
            name="Test Manager",
            email="manager@test.local",
            password_hash=get_password_hash("not-used"),
            role="MANAGER",
        )
        self.db.add_all([room, department, manager])
        self.db.flush()
        now = datetime.utcnow()
        self.db.add(Booking(
            resort_id=resort.id,
            room_id=room.id,
            guest_name="Guest Example",
            guest_email="guest@example.com",
            check_in=now - timedelta(hours=2),
            check_out=now + timedelta(days=2),
            status="checked_in",
            guests_count=2,
        ))
        self.db.commit()
        self.resort_id = resort.id
        self.manager_token = create_access_token({"sub": manager.email, "role": "MANAGER"})

        app = FastAPI()
        app.include_router(router)
        app.include_router(recommendations_router)

        def override_db():
            session = self.Session()
            try:
                yield session
            finally:
                session.close()

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        self.manager_headers = {"Authorization": f"Bearer {self.manager_token}"}

    def tearDown(self):
        self.client.close()
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def start_guest_session(self):
        response = self.client.post("/api/guest-intelligence/session", json={
            "room_number": "A12",
            "guest_name": "Guest Example",
        })
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["access_token"]

    def create_activities(self):
        activities = []
        for index, category in enumerate(("Wellness", "Water", "Dining", "Culture"), start=1):
            response = self.client.post(
                "/api/guest-intelligence/manager/activities",
                headers=self.manager_headers,
                json={
                    "name": f"Experience {index}",
                    "description": f"A resort activity for guests number {index}.",
                    "category": category,
                    "tags": ["relaxation" if index == 1 else "group"],
                    "capacity": 8,
                    "available_slots": 8,
                    "crowd_level": "LOW" if index == 1 else "MODERATE",
                },
            )
            self.assertEqual(response.status_code, 200, response.text)
            activities.append(response.json())
        return activities

    def test_guest_session_recommendations_interactions_and_feedback(self):
        activities = self.create_activities()
        guest_token = self.start_guest_session()
        guest_headers = {"Authorization": f"Bearer {guest_token}"}

        profile_response = self.client.get("/api/guest-intelligence/profiles/me", headers=guest_headers)
        self.assertEqual(profile_response.status_code, 200)
        self.assertNotIn("guest_name", profile_response.json())

        recommendations = self.client.get("/api/guest-intelligence/recommendations", headers=guest_headers)
        self.assertEqual(recommendations.status_code, 200, recommendations.text)
        self.assertEqual(len(recommendations.json()), 4)
        self.assertTrue(all(item["reasons"] for item in recommendations.json()))

        activity_id = activities[0]["id"]
        booked = self.client.post("/api/guest-intelligence/interactions", headers=guest_headers, json={
            "activity_id": activity_id,
            "interaction_type": "BOOKED",
        })
        self.assertEqual(booked.status_code, 200, booked.text)
        self.assertEqual(booked.json()["available_slots"], 7)

        duplicate_booking = self.client.post("/api/guest-intelligence/interactions", headers=guest_headers, json={
            "activity_id": activity_id,
            "interaction_type": "BOOKED",
        })
        self.assertEqual(duplicate_booking.status_code, 409)

        completed = self.client.post("/api/guest-intelligence/interactions", headers=guest_headers, json={
            "activity_id": activity_id,
            "interaction_type": "COMPLETED",
        })
        self.assertEqual(completed.status_code, 200, completed.text)

        rated = self.client.post("/api/guest-intelligence/interactions", headers=guest_headers, json={
            "activity_id": activity_id,
            "interaction_type": "RATED",
            "rating": 5,
        })
        self.assertEqual(rated.status_code, 200, rated.text)

        rebooked = self.client.post("/api/guest-intelligence/interactions", headers=guest_headers, json={
            "activity_id": activity_id,
            "interaction_type": "BOOKED",
        })
        self.assertEqual(rebooked.status_code, 200, rebooked.text)
        canceled = self.client.post("/api/guest-intelligence/interactions", headers=guest_headers, json={
            "activity_id": activity_id,
            "interaction_type": "CANCELLED",
        })
        self.assertEqual(canceled.status_code, 200, canceled.text)
        self.assertEqual(canceled.json()["available_slots"], 7)

        task_count_before_feedback = self.db.query(Task).count()
        feedback = self.client.post("/api/guest-intelligence/feedback", headers=guest_headers, json={
            "comment": "The instructor was rude and the class was crowded.",
            "activity_id": activity_id,
        })
        self.assertEqual(feedback.status_code, 200, feedback.text)
        self.assertEqual(feedback.json()["sentiment"], "NEGATIVE")
        self.assertEqual(self.db.query(Task).count(), task_count_before_feedback)

        manager_report = self.client.get("/api/guest-intelligence/manager/overview", headers=self.manager_headers)
        self.assertEqual(manager_report.status_code, 200, manager_report.text)
        report = manager_report.json()
        self.assertEqual(report["guest_count"], 1)
        topics = {item["topic"] for item in report["feedback"]["recurring_topics"]}
        self.assertIn("crowding", topics)
        self.assertIn("service", topics)
        self.assertNotIn("comment", str(report))
        self.assertNotIn("guest_key", str(report))

    def test_guest_identity_and_manager_data_are_access_controlled(self):
        bad_session = self.client.post("/api/guest-intelligence/session", json={
            "room_number": "A12",
            "guest_name": "Someone Else",
        })
        self.assertEqual(bad_session.status_code, 401)

        guest_token = self.start_guest_session()
        guest_headers = {"Authorization": f"Bearer {guest_token}"}
        denied = self.client.get("/api/guest-intelligence/manager/overview", headers=guest_headers)
        self.assertEqual(denied.status_code, 401)

        unauthenticated = self.client.get("/api/guest-intelligence/profiles/me")
        self.assertEqual(unauthenticated.status_code, 403)

    def test_availability_and_activity_management_validation(self):
        activity = self.create_activities()[0]
        guest_token = self.start_guest_session()
        guest_headers = {"Authorization": f"Bearer {guest_token}"}
        manager_activities = self.client.get(
            "/api/guest-intelligence/manager/activities",
            headers=self.manager_headers,
        )
        self.assertEqual(manager_activities.status_code, 200)
        self.assertEqual(len(manager_activities.json()), 4)

        updated = self.client.patch(
            f"/api/guest-intelligence/manager/activities/{activity['id']}",
            headers=self.manager_headers,
            json={"available_slots": 6, "crowd_level": "HIGH"},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["available_slots"], 6)
        self.assertEqual(updated.json()["crowd_level"], "HIGH")

        guest_activities = self.client.get("/api/guest-intelligence/activities", headers=guest_headers)
        self.assertEqual(guest_activities.status_code, 200, guest_activities.text)
        self.assertEqual(len(guest_activities.json()), 4)

        canceled_booking = self.client.post("/api/guest-intelligence/interactions", headers=guest_headers, json={
            "activity_id": activity["id"],
            "interaction_type": "CANCELLED",
        })
        self.assertEqual(canceled_booking.status_code, 409)

        invalid_capacity = self.client.post(
            "/api/guest-intelligence/manager/activities",
            headers=self.manager_headers,
            json={
                "name": "Invalid capacity",
                "description": "Capacity cannot be below listed availability.",
                "category": "Test",
                "capacity": 2,
                "available_slots": 3,
                "crowd_level": "LOW",
            },
        )
        self.assertEqual(invalid_capacity.status_code, 400)

    def test_similar_historical_stays_support_cold_start_recommendations(self):
        activities = self.create_activities()
        guest_token = self.start_guest_session()
        guest_headers = {"Authorization": f"Bearer {guest_token}"}
        current_booking = self.db.query(Booking).filter(Booking.status == "checked_in").first()

        for index in range(3):
            check_out = datetime.utcnow() - timedelta(days=4 + index)
            historical_booking = Booking(
                resort_id=self.resort_id,
                room_id=current_booking.room_id,
                guest_name=f"Past Guest {index}",
                guest_email=f"past{index}@test.local",
                check_in=check_out - timedelta(days=2 + index),
                check_out=check_out,
                status="checked_out",
                guests_count=2 + (index % 2),
            )
            self.db.add(historical_booking)
            self.db.flush()
            profile = get_or_create_guest_profile(self.db, historical_booking)
            self.db.add(GuestActivityInteraction(
                resort_id=self.resort_id,
                guest_profile_id=profile.id,
                activity_id=activities[0]["id"],
                interaction_type="COMPLETED",
            ))
        self.db.commit()

        recommendations = self.client.get("/api/guest-intelligence/recommendations", headers=guest_headers)
        self.assertEqual(recommendations.status_code, 200, recommendations.text)
        recommended = next(item for item in recommendations.json() if item["activity"]["id"] == activities[0]["id"])
        self.assertIn("similar stay patterns", " ".join(recommended["reasons"]))

        manager_report = self.client.get("/api/guest-intelligence/manager/overview", headers=self.manager_headers)
        self.assertEqual(manager_report.status_code, 200, manager_report.text)
        self.assertEqual(manager_report.json()["guest_count"], 4)

    def test_guest_demo_login_requests_and_training_data_are_isolated(self):
        first_seed = seed_guest_training_data(self.db, self.resort_id)
        self.db.commit()
        second_seed = seed_guest_training_data(self.db, self.resort_id)
        self.db.commit()
        self.assertEqual(first_seed["profiles"], 6)
        self.assertEqual(first_seed["activities"], 4)
        self.assertGreater(first_seed["interactions"], 0)
        self.assertEqual(second_seed["interactions"], 0)
        self.assertEqual(second_seed["feedback"], 0)
        self.assertEqual(second_seed["requests"], 0)
        training_overview = self.client.get(
            "/api/guest-intelligence/manager/overview",
            headers=self.manager_headers,
        )
        self.assertEqual(training_overview.status_code, 200)
        self.assertEqual(training_overview.json()["feedback"]["total"], 0)
        training_topics = {item["topic"] for item in training_overview.json()["feedback"]["training_topics"]}
        self.assertIn("crowding", training_topics)

        login = self.client.post("/api/guest-intelligence/guest-login", json={
            "email": "guest.demo@resort360.com",
            "password": "guest123",
        })
        self.assertEqual(login.status_code, 200, login.text)
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        sample_requests = self.client.get("/api/guest-intelligence/requests/me", headers=headers)
        self.assertEqual(sample_requests.status_code, 200)
        self.assertEqual(len(sample_requests.json()), 3)
        self.assertTrue(all(request["is_training_sample"] for request in sample_requests.json()))

        task_count_before = self.db.query(Task).count()
        submitted = self.client.post("/api/guest-intelligence/requests", headers=headers, json={
            "request_type": "Housekeeping/Towels",
            "description": "Please bring two clean towels to the room.",
            "priority": "MEDIUM",
        })
        self.assertEqual(submitted.status_code, 200, submitted.text)
        self.assertFalse(submitted.json()["is_training_sample"])
        self.assertEqual(self.db.query(Task).count(), task_count_before + 1)

        first_booking = self.db.query(Booking).filter(Booking.status == "checked_in").first()
        other_booking = Booking(
            resort_id=self.resort_id,
            room_id=first_booking.room_id,
            guest_name="Other Guest",
            guest_email="other@test.local",
            check_in=datetime.utcnow() - timedelta(hours=1),
            check_out=datetime.utcnow() + timedelta(days=1),
            status="checked_in",
            guests_count=1,
        )
        self.db.add(other_booking)
        self.db.flush()
        self.db.add(GuestAccount(
            resort_id=self.resort_id,
            booking_id=other_booking.id,
            email="other.guest@test.local",
            password_hash=get_password_hash("guest456"),
        ))
        self.db.commit()
        other_login = self.client.post("/api/guest-intelligence/guest-login", json={
            "email": "other.guest@test.local",
            "password": "guest456",
        })
        self.assertEqual(other_login.status_code, 200, other_login.text)
        other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}
        other_requests = self.client.get("/api/guest-intelligence/requests/me", headers=other_headers)
        self.assertEqual(other_requests.status_code, 200)
        self.assertEqual(other_requests.json(), [])

    def test_inventory_recommendation_approval_creates_purchase_orders(self):
        item = InventoryItem(
            resort_id=self.resort_id,
            name="Synthetic Linen Sets",
            category="Housekeeping",
            unit="sets",
            current_stock=2,
            reorder_threshold=10,
            min_stock=5,
            max_stock=50,
            unit_cost=12.5,
            consumption_rate_per_occupied_room=0.1,
            lead_time_days=2,
        )
        self.db.add(item)
        self.db.flush()

        def create_recommendation(title):
            recommendation = Recommendation(
                resort_id=self.resort_id,
                type="inventory",
                priority="HIGH",
                title=title,
                recommended_action="Reorder synthetic linen stock.",
                explanation="Stock projection is at the reorder threshold.",
                expected_impact="Avoid a linen stockout.",
                metrics_data={
                    "item_id": item.id,
                    "item_name": item.name,
                    "category": item.category,
                    "unit": item.unit,
                    "reorder_quantity": 8,
                },
                status="PENDING",
            )
            self.db.add(recommendation)
            self.db.commit()
            return recommendation

        task_count_before = self.db.query(Task).count()
        first = create_recommendation("Reorder synthetic linen sets")
        approved = self.client.post(
            f"/api/recommendations/{first.id}/approve",
            headers=self.manager_headers,
        )
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()["purchase_orders_created"], 1)
        self.assertEqual(self.db.query(Task).count(), task_count_before)

        first_po = self.db.query(PurchaseOrder).filter(PurchaseOrder.recommendation_id == first.id).one()
        self.assertEqual(first_po.status, "PENDING")
        self.assertEqual(first_po.quantity, 8)
        self.assertEqual(first_po.estimated_cost, 100)
        self.assertEqual(first_po.approved_by, "Test Manager")
        self.assertTrue(self.db.query(ActivityLog).filter(
            ActivityLog.entity_type == "recommendation",
            ActivityLog.entity_id == first.id,
            ActivityLog.action_type == "RECOMMENDATION_APPROVED",
        ).first())

        second = create_recommendation("Modify synthetic linen reorder")
        modified = self.client.post(
            f"/api/recommendations/{second.id}/modify",
            headers=self.manager_headers,
            json={"action": "MODIFY", "modified_quantity": 11, "modified_notes": "Maintain two-week reserve."},
        )
        self.assertEqual(modified.status_code, 200, modified.text)
        second_po = self.db.query(PurchaseOrder).filter(PurchaseOrder.recommendation_id == second.id).one()
        self.assertEqual(second_po.quantity, 11)
        self.assertEqual(second_po.estimated_cost, 137.5)
        self.assertEqual(self.db.query(Task).count(), task_count_before)


if __name__ == "__main__":
    unittest.main()
