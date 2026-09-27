# Smart Resort 360 - AI-Powered Operations Orchestration Platform

**MVP Prototype**: Predictive resort operations management with explainable AI recommendations and closed-loop decision workflow.

---

## 🎯 Core Value Proposition

Smart Resort 360 transforms reactive resort management into **proactive decision-making** through:

- **ML-based occupancy forecasting** (scikit-learn Linear Regression on historical patterns)
- **Predictive staffing gap detection** (workload vs capacity analysis)
- **Inventory stockout prediction** (consumption-based demand forecasting)
- **Explainable AI recommendations** (transparent "Why" + "Impact" rationale)
- **Closed-loop execution** (Approve → Auto-create Tasks/POs → Track → Complete → Audit)

### Key Question Answered:
> **"Will the resort be operationally ready for tomorrow?"**

---

## 🏗️ Architecture

### Tech Stack

**Frontend**
- React 18 + Vite
- Tailwind CSS 3
- React Router 6
- Recharts (data visualization)
- Axios (API client)
- Lucide Icons

**Backend**
- FastAPI (Python)
- SQLAlchemy ORM
- PostgreSQL / SQLite
- Pydantic schemas
- JWT authentication (bcrypt)

**AI/ML Engines**
- pandas + numpy (data processing)
- scikit-learn (Linear Regression for occupancy forecasting)
- Rule-based explainable recommendation engine

**Deployment**
- Frontend: Vercel
- Backend: Render
- Database: Supabase (PostgreSQL) or local SQLite

---

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- npm or yarn

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials (or use default SQLite)

# Seed database with realistic demo data
PYTHONPATH=. python app/database/seed.py

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

Backend will run at: http://localhost:8000
API docs: http://localhost:8000/docs

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Set VITE_API_URL=http://localhost:8000

# Start development server
npm run dev
```

Frontend will run at: http://localhost:3000

---

## 👥 Demo Credentials

The seed script creates demo accounts for the Manager, Front Desk, four Department Heads, and operational staff:

| Role | Email | Password | Access |
|------|-------|----------|--------|
| **Manager** | manager@resort360.com | password123 | Full system access, AI recommendations, approvals |
| **Front Desk** | frontdesk@resort360.com | password123 | Check-ins/outs, room readiness, guest requests |
| **Housekeeping Lead** | housekeeping.head@resort360.com | password123 | Department workload, task assignment |
| **Maintenance Lead** | maintenance.head@resort360.com | password123 | Department workload, task assignment, escalation |
| **Food & Beverage Lead** | fb.head@resort360.com | password123 | Department workload, task assignment, escalation |
| **Inventory Lead** | inventory.head@resort360.com | password123 | Department workload, task assignment, escalation |
| **Guest Demo** | guest.demo@resort360.com | guest123 | Guest recommendations, service requests, activities, feedback |
| **Staff** | staff.elena@resort360.com | password123 | My tasks, status updates |

**Guest Access**: Navigate to `/guest-request` (no login required) to submit QR-style service requests.

## Guest Intelligence MVP

Guests can open `/guest-experiences` and sign in with the Guest Demo account, or verify another active stay with its room number and reservation name. The guest portal groups **Recommended**, **My Requests**, **My Activities**, and **Feedback** in one account. Recommendations use recorded stay context, activity interactions and ratings, listed availability, and manager-maintained crowd levels. Guest responses do not expose another guest's identity.

Managers can open **Guest Intelligence** from the Manager navigation to review aggregate stay segments, 14-day interaction trends, negative feedback topics, and maintain the resort activity catalog. Availability and crowd levels are manager-maintained values, not live telemetry. Feedback sentiment and topic detection is lightweight and does not automatically create operational tasks.

The API is grouped under `/api/guest-intelligence`: guest login/session/profile/activity/recommendation/interaction/feedback/request endpoints and Manager-only activity management and aggregate overview endpoints. The demo seed includes four labeled training activities, six pseudonymous training profiles with interaction/feedback history, and three labeled Guest Demo requests. These samples are kept out of live operations queues and live trend/feedback aggregates. New tables and training flags are added without dropping existing V1/V2 tables.

---

## 📊 Core Features Demonstrated

### 1. Manager Dashboard (`/dashboard`)
- Real-time KPIs: occupancy, arrivals, critical tasks
- **Explainable AI recommendations** with "Why" + "Expected Impact"
- Approve/Reject/Modify workflow (closed-loop execution)
- Room status breakdown
- Recent activity audit stream

### 2. 7-Day Forecast (`/forecast`)
- **ML occupancy prediction** using Linear Regression trained on historical bookings
- Check-in/check-out projections
- Housekeeping cleaning workload vs scheduled capacity
- Staffing gap identification
- Revenue estimates
- Model confidence scores

### 3. Inventory & Purchase Orders (`/inventory`)
- ML-driven stockout risk analysis (CRITICAL/HIGH/MEDIUM/LOW)
- Consumption rate × occupancy forecast
- Days-until-stockout calculation
- Auto-generated purchase order tracker
- Receive & restock workflow

### 4. Closed-Loop Workflow

**Example: Staffing Recommendation**
```
Tomorrow occupancy = 95% (68 check-ins, 31 check-outs, 18 early arrivals)
   ↓
AI detects: 93 rooms to clean, current capacity = 68 rooms
   ↓
Recommendation: "Add 2 housekeepers tomorrow"
   ↓
Manager approves (or modifies to 3 housekeepers)
   ↓
System auto-creates 2 housekeeping shift tasks
   ↓
Department Head assigns to available staff
   ↓
Staff accepts → starts → completes
   ↓
Activity log records entire decision chain
```

### 5. Guest Request Portal (`/guest-request`)
- QR-accessible lightweight form
- Requests automatically routed to appropriate department
- Creates operational task in closed-loop system

### 6. Activity Log (`/activity-log`)
- Filterable audit trail
- Tracks recommendations approved/rejected
- Task assignments and completions
- Purchase order fulfillment

---

## 🔬 AI/ML Implementation Details

### Occupancy Forecasting Engine

**Approach**: Light ML using scikit-learn `LinearRegression`

**Training Data**:
- 90 days of historical booking patterns
- Features: `day_of_week`, `is_weekend`, `day_of_month`, `month`, `lagged_1d`, `lagged_7d`
- Target: `occupancy_pct`

**Prediction**:
- Combines confirmed bookings with ML predictions
- Confidence scores based on R² score
- Handles edge cases (insufficient data → baseline 65%)

**Code**: `backend/app/services/forecast_engine.py`

### Staffing Recommendation Engine

**Formula**:
```
Rooms to clean = Check-outs + Dirty rooms + Early arrivals
Required housekeepers = ceil(Rooms to clean / 10)
Staffing gap = Required - Scheduled
```

**Priority Assignment**:
- Gap ≥ 3: CRITICAL
- Gap ≥ 1: HIGH
- Gap = 0: LOW

**Code**: `backend/app/services/staffing_engine.py`

### Inventory Stockout Prediction

**Formula**:
```
Projected consumption = Σ(occupied_rooms × consumption_rate_per_room)
Days until stockout = current_stock / daily_consumption
Risk = CRITICAL if days < lead_time
```

**Code**: `backend/app/services/inventory_engine.py`

---

## 📁 Project Structure

```
Smart-Resort-360/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry
│   │   ├── models/              # SQLAlchemy models
│   │   ├── routes/              # API endpoints
│   │   ├── services/            # AI/ML engines
│   │   │   ├── forecast_engine.py
│   │   │   ├── staffing_engine.py
│   │   │   ├── inventory_engine.py
│   │   │   └── recommendation_engine.py
│   │   ├── database/
│   │   │   ├── connection.py
│   │   │   └── seed.py          # Synthetic data generator
│   │   ├── schemas.py           # Pydantic schemas
│   │   └── utils/
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Router + auth wrapper
│   │   ├── components/
│   │   │   ├── Navbar.jsx
│   │   │   └── RecommendationCard.jsx
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── ManagerDashboard.jsx
│   │   │   ├── FrontDeskDashboard.jsx
│   │   │   ├── DepartmentDashboard.jsx
│   │   │   ├── StaffDashboard.jsx
│   │   │   ├── Forecast.jsx
│   │   │   ├── Inventory.jsx
│   │   │   ├── ActivityLog.jsx
│   │   │   └── GuestRequest.jsx
│   │   ├── services/
│   │   │   └── api.js           # Axios API client
│   │   ├── contexts/
│   │   │   └── AuthContext.jsx
│   │   └── utils/
│   │       └── helpers.js
│   ├── package.json
│   └── .env
│
└── README.md
```

---

## 🧪 Testing the MVP

### Scenario 1: Manager Approves Staffing Recommendation
1. Login as `manager@resort360.com`
2. View pending AI recommendations on dashboard
3. Review "Add 2 housekeepers" recommendation with explainable rationale
4. Click **Approve** → System creates 2 tasks
5. Switch to `housekeeping.head@resort360.com`
6. See new tasks in department workload
7. Assign tasks to staff members
8. Switch to `staff.elena@resort360.com`
9. Update task status: Pending → In Progress → Completed
10. Return to manager dashboard → View activity log

### Scenario 2: Inventory Stockout Prevention
1. Navigate to `/inventory`
2. View items with HIGH/CRITICAL stockout risk
3. Check projected days until stockout
4. AI auto-generated purchase order recommendations
5. Manager approves → PO created
6. Mark PO as "Received" → Inventory restocked

### Scenario 3: Guest Submits Maintenance Request
1. Navigate to `/guest-request` (no login)
2. Enter room number: 109
3. Select "AC/Maintenance"
4. Describe: "Air conditioning blowing lukewarm air"
5. Submit → Request routed to Maintenance department
6. Login as maintenance department head
7. See request as operational task
8. Assign to technician
9. Technician completes work

---

## 🎨 Design Principles

### Explainable AI
Every recommendation includes:
- **Recommended Action**: What to do
- **Why (Rationale)**: Data-driven reasoning
- **Expected Impact**: Operational outcome

### Closed-Loop Workflow
```
Prediction → Recommendation → Human Approval → Automated Execution → Tracking → Audit
```

### Role-Based Access
- Manager: strategic oversight
- Department Heads: tactical execution
- Staff: operational work
- Guests: lightweight request submission

---

## 🔐 Security Notes

**For MVP Demo**:
- Demo credentials are intentionally simple
- JWT tokens with 24-hour expiration
- bcrypt password hashing

**Production Considerations**:
- Implement OAuth2/SSO
- Add rate limiting
- Enable HTTPS only
- Environment variable secrets management
- Database connection pooling
- CORS whitelist specific domains

---

## 📈 Future Enhancements (Post-MVP)

- **Real PMS Integration** (Opera, Mews, Cloudbeds)
- **Deep Learning** time series forecasting (LSTM)
- **Predictive Maintenance** (equipment failure prediction)
- **Dynamic Pricing** engine
- **Mobile Apps** (iOS/Android)
- **Real-time WebSocket** updates
- **Multi-property** management
- **Advanced RBAC** with granular permissions
- **Guest Portal** with loyalty program
- **Vendor API** integration for auto-ordering

---

## 📝 API Documentation

Once backend is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

```
POST   /api/auth/login
GET    /api/dashboard/manager
GET    /api/forecast/occupancy?days=7
GET    /api/recommendations
POST   /api/recommendations/{id}/approve
POST   /api/recommendations/{id}/modify
GET    /api/tasks
PATCH  /api/tasks/{id}/status
GET    /api/inventory
POST   /api/guest-requests
GET    /api/activity-log
POST   /api/demo/reset
```

---

## 🐛 Troubleshooting

### Backend Issues

**Database connection error**:
```bash
# Check .env DATABASE_URL
# For SQLite (default): DATABASE_URL=sqlite:///./resort360.db
# For PostgreSQL: DATABASE_URL=postgresql://user:pass@host:port/dbname
```

**Module import errors**:
```bash
# Run with PYTHONPATH set
PYTHONPATH=. python app/database/seed.py
PYTHONPATH=. uvicorn app.main:app --reload
```

### Frontend Issues

**API connection refused**:
- Ensure backend is running on port 8000
- Check `.env` file: `VITE_API_URL=http://localhost:8000`

---

## Production Deployment (Vercel + Render + PostgreSQL)

Deployment manifests are provided in `frontend/vercel.json` and the repository-root `render.yaml`. No public deployment is configured by this repository alone; the deployment owner must connect the project and provide the service-specific values below.

### Vercel

Set the Vercel project root to `frontend`. The Vite build outputs `dist`, and `vercel.json` rewrites browser routes to `index.html` so direct links and refreshes work. Configure this public build variable:

| Variable | Value |
|---|---|
| `VITE_API_URL` | The HTTPS origin of the deployed Render API, for example `https://your-api-service.onrender.com` |

Production frontend builds fail if `VITE_API_URL` is missing. Do not put database URLs, JWT secrets, or service-role keys in Vercel frontend variables.

### Render API

Create a Render Blueprint from `render.yaml` or create a Web Service with root directory `backend`, Python 3.11.9, build command `pip install -r requirements.txt`, start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`, and health path `/health`. Configure these values in Render; never commit their values:

| Variable | Required value |
|---|---|
| `APP_ENV` | `production` |
| `DATABASE_URL` | PostgreSQL connection string from Supabase or another managed PostgreSQL provider |
| `SECRET_KEY` | Unique generated signing secret (Render Blueprint generates one) |
| `CORS_ORIGINS` | Exact HTTPS Vercel production origin(s), comma-separated; no wildcard |
| `DEMO_ACCOUNT_PASSWORD` | Unique password of at least 16 characters for seeded staff/manager demo accounts |
| `GUEST_DEMO_PASSWORD` | Unique password of at least 16 characters for the seeded guest demo account |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Optional; Blueprint sets 60 |

The backend refuses to start in production without PostgreSQL, a strong JWT secret, or explicit CORS origins. `/health` executes a database query and returns `503` when PostgreSQL is unavailable. Demo reset/seed endpoints are disabled in production.

### Initial Synthetic Data

After setting the Render environment variables and confirming the PostgreSQL connection, run this **one-time** command from the backend service shell or a secure local environment configured with the production `DATABASE_URL` and password variables:

```bash
python -m app.database.seed
```

The default seed is additive and skips seeding if a resort already exists. It does not delete data. `python -m app.database.seed --reset` is destructive and is refused in production. New tables are created additively on startup. Back up PostgreSQL before any schema or seed operation.

### What Has and Has Not Been Verified

The local verification checks backend tests, frontend builds, and live local API workflows. A real Vercel/Render deployment, external PostgreSQL credentials/networking, production CORS origin, and public URL cannot be marked verified until those deployment values are configured and tested in the provider dashboards. Do not treat local SQLite or localhost checks as proof of production persistence.

**Build errors**:
```bash
rm -rf node_modules package-lock.json
npm install
npm run build
```

---

## 📄 License

This is an MVP prototype for demonstration purposes.

---

## 👤 Contact

For questions about this MVP implementation, please refer to the codebase documentation and inline comments.

---

## 🎯 MVP Success Criteria ✅

- [x] Multi-role authentication system
- [x] ML-based occupancy forecasting (scikit-learn)
- [x] Predictive staffing recommendations
- [x] Inventory stockout prediction
- [x] Explainable AI rationale ("Why" + "Impact")
- [x] Closed-loop approval → execution workflow
- [x] Manager approve/reject/modify recommendations
- [x] Auto-creation of tasks/purchase orders
- [x] Department Head task assignment
- [x] Staff task status updates
- [x] Guest request submission portal
- [x] Comprehensive activity audit log
- [x] Recharts data visualization
- [x] Persistent database (SQLite/PostgreSQL)
- [x] RESTful API with FastAPI
- [x] Responsive React frontend
- [x] Role-based access control
- [x] Public deployment-ready architecture

**The resort operations intelligence layer is now operational.** 🚀
