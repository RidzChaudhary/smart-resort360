"""
Live System Health & Crucial Failure Diagnostic Suite.
Tests all live API endpoints using TestClient against the seeded SQLite database.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import SessionLocal
from app.models import User, Resort
from app.utils.auth import create_access_token


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="module")
def manager_headers(db_session):
    manager = db_session.query(User).filter(User.role == "MANAGER").first()
    assert manager is not None, "Manager user must exist in database"
    token = create_access_token({"sub": manager.email, "role": manager.role, "resort_id": manager.resort_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def frontdesk_headers(db_session):
    user = db_session.query(User).filter(User.role == "FRONT_DESK").first()
    assert user is not None, "Front desk user must exist in database"
    token = create_access_token({"sub": user.email, "role": user.role, "resort_id": user.resort_id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def depthead_headers(db_session):
    user = db_session.query(User).filter(User.role == "DEPARTMENT_HEAD").first()
    assert user is not None, "Department Head user must exist in database"
    token = create_access_token({"sub": user.email, "role": user.role, "resort_id": user.resort_id, "department_id": user.department_id})
    return {"Authorization": f"Bearer {token}"}


class TestLiveSystemHealth:

    def test_01_health_and_root(self, client):
        response = client.get("/")
        # If root route exists or doc url
        assert response.status_code in (200, 404)

    def test_02_auth_login(self, client):
        response = client.post("/api/auth/login", json={"email": "manager@resort360.com", "password": "password123"})
        assert response.status_code == 200, f"Manager login failed: {response.text}"
        data = response.json()
        assert "access_token" in data

    def test_03_dashboard_overview(self, client, manager_headers):
        response = client.get("/api/dashboard/manager", headers=manager_headers)
        assert response.status_code == 200, f"Dashboard overview failed: {response.text}"
        data = response.json()
        assert "kpis" in data or "pending_recommendations" in data

    def test_04_forecast_7day(self, client, manager_headers):
        response = client.get("/api/forecast/occupancy", headers=manager_headers)
        assert response.status_code == 200, f"Forecast failed: {response.text}"

    def test_05_weather_current_and_risk(self, client, manager_headers):
        res_current = client.get("/api/weather/current", headers=manager_headers)
        assert res_current.status_code == 200, f"Weather current failed: {res_current.text}"
        
        res_risk = client.get("/api/weather/risk-analysis", headers=manager_headers)
        assert res_risk.status_code == 200, f"Weather risk analysis failed: {res_risk.text}"

    def test_06_digital_twin_state_and_simulation(self, client, manager_headers):
        res_state = client.get("/api/digital-twin/state", headers=manager_headers)
        assert res_state.status_code == 200, f"Digital twin state failed: {res_state.text}"

        res_sim = client.post(
            "/api/digital-twin/simulate",
            headers=manager_headers,
            json={
                "rain_probability": 46.0,
                "rain_intensity_mm": 4.0,
                "wind_speed_kmh": 25.0,
                "duration_hours": 3
            }
        )
        assert res_sim.status_code == 200, f"Digital twin simulation failed: {res_sim.text}"
        sim_data = res_sim.json()
        assert "impact_analysis" in sim_data
        assert "affected_guests" in sim_data["impact_analysis"]

    def test_07_inventory_items_and_pos(self, client, manager_headers):
        res_inv = client.get("/api/inventory", headers=manager_headers)
        assert res_inv.status_code == 200, f"Inventory items failed: {res_inv.text}"
        
        res_pos = client.get("/api/inventory/purchase-orders", headers=manager_headers)
        assert res_pos.status_code == 200, f"Inventory purchase orders failed: {res_pos.text}"

    def test_08_front_desk_and_tasks(self, client, manager_headers):
        res_tasks = client.get("/api/tasks", headers=manager_headers)
        assert res_tasks.status_code == 200, f"Tasks failed: {res_tasks.text}"

    def test_09_guest_intelligence_overview(self, client, manager_headers):
        res_gi = client.get("/api/guest-intelligence/manager/overview", headers=manager_headers)
        assert res_gi.status_code == 200, f"Guest intelligence overview failed: {res_gi.text}"

    def test_10_activity_log(self, client, manager_headers):
        res_logs = client.get("/api/activity-log", headers=manager_headers)
        assert res_logs.status_code == 200, f"Activity logs failed: {res_logs.text}"
