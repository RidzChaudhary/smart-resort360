import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.models import Booking, Department, Room, User

class ForecastEngine:
    """
    Light ML forecasting engine using Linear Regression for occupancy prediction.
    Combines confirmed bookings with historical pattern-based predictions.
    """

    def __init__(self, db: Session, resort_id: int):
        self.db = db
        self.resort_id = resort_id
        self.model = LinearRegression()
        self.scaler = StandardScaler()
        self.model_trained = False
        self.model_r2_score = None

    def get_room_capacity(self) -> Dict[str, int]:
        """Return physical and currently sellable room capacity."""
        total_rooms = self.db.query(Room).filter(Room.resort_id == self.resort_id).count()
        unavailable_rooms = self.db.query(Room).filter(
            and_(Room.resort_id == self.resort_id, Room.status.in_(["maintenance", "out_of_service"]))
        ).count()
        return {
            "total_rooms": total_rooms or 100,
            "unavailable_rooms": unavailable_rooms,
            "sellable_rooms": max((total_rooms or 100) - unavailable_rooms, 0),
        }

    def get_historical_occupancy_data(self, days_back: int = 90) -> pd.DataFrame:
        """
        Extract historical occupancy patterns from bookings.
        Returns DataFrame with: date, day_of_week, occupied_rooms, occupancy_pct
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)

        # Get all bookings that overlapped with historical period
        bookings = self.db.query(Booking).filter(
            and_(
                Booking.resort_id == self.resort_id,
                Booking.check_in <= end_date,
                Booking.check_out >= start_date,
                Booking.status.in_(["confirmed", "checked_in", "checked_out"])
            )
        ).all()

        # Get total rooms
        capacity = self.get_room_capacity()
        total_rooms = capacity["sellable_rooms"]

        # Build daily occupancy records
        records = []
        current_date = start_date

        while current_date <= end_date:
            occupied = 0
            for booking in bookings:
                # Check if booking was active on this date
                if booking.check_in.date() <= current_date.date() < booking.check_out.date():
                    occupied += 1

            records.append({
                'date': current_date.date(),
                'day_of_week': current_date.weekday(),  # 0=Monday, 6=Sunday
                'is_weekend': 1 if current_date.weekday() >= 5 else 0,
                'day_of_month': current_date.day,
                'month': current_date.month,
                'occupied_rooms': occupied,
                'occupancy_pct': (occupied / total_rooms * 100) if total_rooms > 0 else 0
            })
            current_date += timedelta(days=1)

        return pd.DataFrame(records)

    def train_model(self, historical_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Train Linear Regression model on historical occupancy patterns.
        Features: day_of_week, is_weekend, day_of_month, month, lagged_occupancy
        Target: occupancy_pct
        """
        if len(historical_df) < 14:
            self.model_trained = False
            self.model_r2_score = None
            # Not enough data for reliable training
            return {
                "model_trained": False,
                "reason": "insufficient_historical_data",
                "samples": len(historical_df)
            }

        # Create lagged features (previous day's occupancy)
        historical_df['lagged_1d'] = historical_df['occupancy_pct'].shift(1)
        historical_df['lagged_7d'] = historical_df['occupancy_pct'].shift(7)

        # Drop rows with NaN from lagging
        df_train = historical_df.dropna()

        if len(df_train) < 10:
            self.model_trained = False
            self.model_r2_score = None
            return {
                "model_trained": False,
                "reason": "insufficient_data_after_lagging",
                "samples": len(df_train)
            }

        # Feature engineering
        features = ['day_of_week', 'is_weekend', 'day_of_month', 'month', 'lagged_1d', 'lagged_7d']
        X = df_train[features]
        y = df_train['occupancy_pct']

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train model
        self.model.fit(X_scaled, y)

        # Calculate training score (R²)
        train_score = self.model.score(X_scaled, y)
        self.model_trained = True
        self.model_r2_score = float(train_score)

        return {
            "model_trained": True,
            "samples": len(df_train),
            "r2_score": float(train_score),
            "features": features,
            "model_type": "LinearRegression"
        }

    def predict_occupancy(self, target_date: datetime, recent_occupancy: float = None) -> Tuple[float, float]:
        """
        Predict occupancy percentage for a target date.
        Returns: (predicted_occupancy_pct, confidence_score)
        """
        # Prepare features for target date
        day_of_week = target_date.weekday()
        is_weekend = 1 if day_of_week >= 5 else 0
        day_of_month = target_date.day
        month = target_date.month

        # Use recent occupancy if available, otherwise use average
        lagged_1d = recent_occupancy if recent_occupancy is not None else 0.0
        lagged_7d = lagged_1d  # Simplified for MVP

        # Create feature vector
        features = np.array([[day_of_week, is_weekend, day_of_month, month, lagged_1d, lagged_7d]])

        try:
            features_scaled = self.scaler.transform(features)
            prediction = self.model.predict(features_scaled)[0]

            # Clamp prediction between 0-100
            prediction = max(0.0, min(100.0, prediction))

            confidence = max(0.0, min(1.0, self.model_r2_score or 0.0))

            return prediction, confidence

        except Exception:
            # If the model cannot be used, carry forward observed occupancy only.
            return max(0.0, min(100.0, recent_occupancy or 0.0)), 0.0

    def get_confirmed_occupancy(self, target_date: datetime) -> Dict[str, int]:
        """
        Get confirmed occupancy data from bookings for a specific date.
        Returns: occupied_rooms, check_ins, check_outs, early_arrivals
        """
        target_date_only = target_date.date()

        # Rooms occupied on target date (check_in <= target < check_out)
        occupied = self.db.query(func.count(func.distinct(Booking.room_id))).filter(
            and_(
                Booking.resort_id == self.resort_id,
                Booking.check_in <= target_date,
                Booking.check_out > target_date,
                Booking.status.in_(["confirmed", "checked_in"])
            )
        ).scalar() or 0

        # Check-ins on target date
        check_ins = self.db.query(func.count(Booking.id)).filter(
            and_(
                Booking.resort_id == self.resort_id,
                func.date(Booking.check_in) == target_date_only,
                Booking.status.in_(["confirmed", "checked_in"])
            )
        ).scalar() or 0

        # Check-outs on target date
        check_outs = self.db.query(func.count(Booking.id)).filter(
            and_(
                Booking.resort_id == self.resort_id,
                func.date(Booking.check_out) == target_date_only,
                Booking.status.in_(["confirmed", "checked_in", "checked_out"])
            )
        ).scalar() or 0

        # Early arrivals (bookings with early_arrival flag on target date)
        early_arrivals = self.db.query(func.count(Booking.id)).filter(
            and_(
                Booking.resort_id == self.resort_id,
                func.date(Booking.check_in) == target_date_only,
                Booking.early_arrival == True,
                Booking.status.in_(["confirmed", "checked_in"])
            )
        ).scalar() or 0

        booking_demand = self.db.query(func.count(Booking.id)).filter(
            and_(
                Booking.resort_id == self.resort_id,
                Booking.check_in <= target_date,
                Booking.check_out > target_date,
                Booking.status.in_(["confirmed", "checked_in"])
            )
        ).scalar() or 0

        return {
            "occupied_rooms": occupied,
            "booking_demand_count": booking_demand,
            "check_ins": check_ins,
            "check_outs": check_outs,
            "early_arrivals": early_arrivals
        }

    def generate_forecast(self, days: int = 7) -> Dict[str, Any]:
        """
        Generate 7-day occupancy forecast combining ML predictions with confirmed bookings.
        """
        if not 1 <= days <= 30:
            raise ValueError("Forecast days must be between 1 and 30")

        # Get total rooms
        capacity = self.get_room_capacity()
        total_rooms = capacity["total_rooms"]
        sellable_rooms = capacity["sellable_rooms"]

        # Get and train on historical data
        historical_df = self.get_historical_occupancy_data(days_back=90)
        model_metadata = self.train_model(historical_df)

        # Use the recent observed mean as the baseline if there is insufficient history to train.
        recent_occupancy = 0.0
        if len(historical_df) > 0:
            recent_occupancy = float(historical_df['occupancy_pct'].tail(7).mean())

        historical_bookings = self.db.query(Booking).filter(
            Booking.resort_id == self.resort_id,
            Booking.revenue > 0,
            Booking.status.in_(["confirmed", "checked_in", "checked_out"]),
        ).all()
        room_night_rates = [
            booking.revenue / max((booking.check_out.date() - booking.check_in.date()).days, 1)
            for booking in historical_bookings
        ]
        historical_rate = float(np.mean(room_night_rates)) if room_night_rates else 0.0

        housekeeping_department = self.db.query(Department).filter(
            Department.resort_id == self.resort_id,
            Department.name.ilike("%housekeeping%"),
        ).first()
        housekeepers_on_roster = self.db.query(func.count(User.id)).filter(
            User.resort_id == self.resort_id,
            User.department_id == housekeeping_department.id if housekeeping_department else None,
            User.role == "STAFF",
        ).scalar() if housekeeping_department else 0

        forecast_days = []
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        for i in range(days):
            target_date = today + timedelta(days=i)

            # Get confirmed booking data
            confirmed_data = self.get_confirmed_occupancy(target_date)

            # Separate physical occupancy from booking demand
            booking_demand_count = confirmed_data["booking_demand_count"]
            overbooking_count = max(0, booking_demand_count - sellable_rooms)

            # If we have confirmed bookings, use them; otherwise predict
            if booking_demand_count > 0:
                # Physical occupancy CANNOT exceed total rooms (cap at 100%)
                actual_occupied = min(confirmed_data["occupied_rooms"], sellable_rooms)
                occupancy_pct = (actual_occupied / sellable_rooms) * 100 if sellable_rooms else 0
                ml_confidence = 1.0  # High confidence for confirmed bookings
            else:
                # Use ML prediction (already capped at 100% in predict_occupancy)
                occupancy_pct, ml_confidence = self.predict_occupancy(target_date, recent_occupancy)
                occupancy_pct = min(100.0, occupancy_pct)  # Extra safety cap
                actual_occupied = int((occupancy_pct / 100) * sellable_rooms)
                booking_demand_count = actual_occupied
                overbooking_count = 0

            # Calculate cleaning workload (based on turnover, not occupancy)
            stay_overs = actual_occupied - confirmed_data["check_ins"]
            cleaning_workload = confirmed_data["check_outs"] + confirmed_data["early_arrivals"]

            # Calculate staffing needs (1 housekeeper can clean ~10 rooms per shift)
            rooms_per_housekeeper = 10
            housekeepers_needed = int(np.ceil(cleaning_workload / rooms_per_housekeeper))

            housekeepers_scheduled = housekeepers_on_roster or 0
            staffing_gap = max(0, housekeepers_needed - housekeepers_scheduled)

            active_bookings = self.db.query(Booking).filter(
                Booking.resort_id == self.resort_id,
                Booking.check_in <= target_date,
                Booking.check_out > target_date,
                Booking.status.in_(["confirmed", "checked_in"]),
            ).all()
            confirmed_revenue = sum(
                booking.revenue / max((booking.check_out.date() - booking.check_in.date()).days, 1)
                for booking in active_bookings
            )
            expected_revenue = confirmed_revenue if confirmed_revenue > 0 else actual_occupied * historical_rate

            forecast_days.append({
                "date": target_date.strftime("%Y-%m-%d"),
                "day_name": target_date.strftime("%A"),
                "predicted_occupancy_pct": round(occupancy_pct, 2),  # Always ≤ 100%
                "occupied_rooms": actual_occupied,  # Physical rooms occupied (capped)
                "booking_demand_count": booking_demand_count,  # Total bookings (can exceed capacity)
                "overbooking_count": overbooking_count,  # Bookings beyond capacity
                "total_rooms": total_rooms,
                "sellable_rooms": sellable_rooms,
                "check_ins": confirmed_data["check_ins"],
                "check_outs": confirmed_data["check_outs"],
                "early_arrivals": confirmed_data["early_arrivals"],
                "stay_overs": max(0, stay_overs),
                "cleaning_workload_rooms": cleaning_workload,
                "housekeepers_needed": housekeepers_needed,
                "housekeepers_scheduled": housekeepers_scheduled,
                "staffing_gap": staffing_gap,
                "expected_revenue": expected_revenue,
                "ml_confidence_score": round(ml_confidence, 2)
            })

            # Update recent occupancy for next iteration
            recent_occupancy = occupancy_pct

        # Overall summary
        total_check_ins = sum(d["check_ins"] for d in forecast_days)
        total_check_outs = sum(d["check_outs"] for d in forecast_days)
        avg_occupancy = sum(d["predicted_occupancy_pct"] for d in forecast_days) / days
        peak_day = max(forecast_days, key=lambda x: x["predicted_occupancy_pct"])
        total_revenue = sum(d["expected_revenue"] for d in forecast_days)

        return {
            "forecast_days": forecast_days,
            "overall_summary": {
                "total_check_ins": total_check_ins,
                "total_check_outs": total_check_outs,
                "total_check_ins_7d": total_check_ins,
                "total_check_outs_7d": total_check_outs,
                "forecast_days": days,
                "avg_occupancy_pct": round(avg_occupancy, 2),
                "peak_occupancy_date": peak_day["date"],
                "peak_occupancy_pct": peak_day["predicted_occupancy_pct"],
                "total_expected_revenue": total_revenue,
                "total_expected_revenue_7d": total_revenue,
                "total_rooms": total_rooms,
                "sellable_rooms": sellable_rooms
            },
            "model_metadata": model_metadata
        }

    def generate_7day_forecast(self) -> Dict[str, Any]:
        """Backward-compatible seven-day forecast used by internal engines."""
        return self.generate_forecast(7)
