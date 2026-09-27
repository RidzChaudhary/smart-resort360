from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List

from app.database.connection import get_db
from app.models import ActivityLog, User
from app.schemas import ActivityLogResponse
from app.utils.auth import require_role

router = APIRouter(prefix="/api/activity-log", tags=["Activity Log"])

@router.get("", response_model=List[ActivityLogResponse])
def get_activity_logs(
    limit: int = 100,
    action_type: str = None,
    current_user: User = Depends(require_role(["MANAGER"])),
    db: Session = Depends(get_db)
):
    """
    Get activity audit logs for the resort.
    Tracks all significant operational actions:
    - Recommendations approved/rejected/modified
    - Tasks created/assigned/completed
    - Purchase orders created/received
    - Guest requests submitted
    - System events

    Optional filters:
    - limit: number of records (default 100, max 500)
    - action_type: filter by specific action type
    """
    resort_id = current_user.resort_id

    query = db.query(ActivityLog).filter(ActivityLog.resort_id == resort_id)

    if action_type:
        query = query.filter(ActivityLog.action_type == action_type.upper())

    logs = query.order_by(desc(ActivityLog.created_at)).limit(min(limit, 500)).all()

    return logs
