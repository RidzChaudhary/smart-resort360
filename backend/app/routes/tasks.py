from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List
from datetime import datetime, timedelta

from app.database.connection import get_db
from app.models import User, Task, Department, ActivityLog
from app.schemas import TaskResponse, TaskCreate, TaskAssignRequest, TaskStatusRequest, TaskEscalateRequest
from app.utils.auth import get_current_user, get_department_head_department_id
TASK_STATUSES = {"PENDING", "ASSIGNED", "IN_PROGRESS", "BLOCKED", "ESCALATED", "COMPLETED", "CANCELLED"}
TASK_TRANSITIONS = {
    "PENDING": {"ASSIGNED", "CANCELLED"},
    "ASSIGNED": {"IN_PROGRESS", "BLOCKED", "CANCELLED"},
    "IN_PROGRESS": {"BLOCKED", "COMPLETED", "CANCELLED"},
    "BLOCKED": {"IN_PROGRESS", "ESCALATED", "CANCELLED"},
    "ESCALATED": {"ASSIGNED", "IN_PROGRESS", "CANCELLED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
}

def serialize_task(task: Task):
    return {
        "id": task.id,
        "resort_id": task.resort_id,
        "recommendation_id": task.recommendation_id,
        "department_id": task.department_id,
        "department_name": task.department.name if task.department else None,
        "assigned_to": task.assigned_to,
        "assignee_name": task.assignee.name if task.assignee else "Unassigned",
        "title": task.title,
        "description": task.description,
        "priority": task.priority,
        "status": task.status,
        "due_date": task.due_date,
        "sla_minutes": task.sla_minutes,
        "room_number": task.room_number,
        "blocker_reason": task.blocker_reason,
        "escalated_to_user_id": task.escalated_to_user_id,
        "escalated_at": task.escalated_at,
        "is_overdue": task.is_overdue,
        "minutes_overdue": task.minutes_overdue,
        "created_at": task.created_at,
        "completed_at": task.completed_at,
    }

def scoped_task_query(query, current_user: User):
    if current_user.role == "MANAGER":
        return query
    if current_user.role == "STAFF":
        return query.filter(Task.assigned_to == current_user.id)
    if current_user.role == "DEPARTMENT_HEAD":
        department_id = get_department_head_department_id(current_user)
        return query.filter(Task.department_id == department_id)
    if current_user.role == "FRONT_DESK":
        return query.join(Department).filter(Department.name.ilike("%front desk%"))
    raise HTTPException(status_code=403, detail="Role cannot access operational tasks")

def can_manage_task(task: Task, current_user: User):
    if current_user.role == "MANAGER":
        return True
    return (
        current_user.role == "DEPARTMENT_HEAD"
        and get_department_head_department_id(current_user) == task.department_id
    )

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

@router.get("", response_model=List[TaskResponse])
def get_tasks(
    department_id: int = None,
    status: str = None,
    assigned_to: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get tasks with optional filters:
    - department_id: filter by department
    - status: PENDING, IN_PROGRESS, COMPLETED, CANCELLED
    - assigned_to: filter by assigned staff user ID
    """
    resort_id = current_user.resort_id

    query = db.query(Task).filter(Task.resort_id == resort_id)
    query = scoped_task_query(query, current_user)

    if department_id:
        query = query.filter(Task.department_id == department_id)

    if status:
        query = query.filter(Task.status == status.upper())

    if assigned_to:
        query = query.filter(Task.assigned_to == assigned_to)

    tasks = query.order_by(Task.priority.desc(), Task.created_at.desc()).all()

    return [serialize_task(task) for task in tasks]


@router.post("", response_model=TaskResponse)
def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually create a new operational task.
    """
    resort_id = current_user.resort_id
    if current_user.role != "MANAGER":
        raise HTTPException(status_code=403, detail="Only managers can create tasks")

    department = db.query(Department).filter(
        Department.id == task_in.department_id,
        Department.resort_id == resort_id,
    ).first()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    assigned_staff = None
    if task_in.assigned_to:
        assigned_staff = db.query(User).filter(
            User.id == task_in.assigned_to,
            User.resort_id == resort_id,
        ).first()
        if not assigned_staff or assigned_staff.role != "STAFF" or assigned_staff.department_id != department.id:
            raise HTTPException(status_code=400, detail="Task must be assigned to staff in its department")

    # Calculate SLA if not provided
    sla_minutes = task_in.sla_minutes
    if not sla_minutes:
        # Default SLA by priority
        sla_map = {"CRITICAL": 60, "HIGH": 120, "MEDIUM": 240, "LOW": 480}
        sla_minutes = sla_map.get(task_in.priority or "MEDIUM", 240)

    # Calculate due_date from SLA if not explicitly provided
    due_date = task_in.due_date
    if not due_date and sla_minutes:
        due_date = datetime.utcnow() + timedelta(minutes=sla_minutes)

    task = Task(
        resort_id=resort_id,
        department_id=task_in.department_id,
        assigned_to=task_in.assigned_to,
        title=task_in.title,
        description=task_in.description,
        priority=task_in.priority or "MEDIUM",
        due_date=due_date,
        sla_minutes=sla_minutes,
        room_number=task_in.room_number,
        status="ASSIGNED" if task_in.assigned_to else "PENDING"
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Log action
    log = ActivityLog(
        resort_id=resort_id,
        user_id=current_user.id,
        user_name=current_user.name,
        user_role=current_user.role,
        action_type="TASK_CREATED",
        entity_type="task",
        entity_id=task.id,
        description=f"{current_user.name} created task: '{task.title}'",
        details_json={"task_id": task.id, "department_id": task.department_id}
    )
    db.add(log)
    db.commit()

    return serialize_task(task)


@router.patch("/{task_id}/assign")
def assign_task(
    task_id: int,
    request: TaskAssignRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Assign or reassign task to a staff member.
    Department Head / Manager role endpoint.
    """
    resort_id = current_user.resort_id

    task = db.query(Task).filter(
        and_(Task.id == task_id, Task.resort_id == resort_id)
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not can_manage_task(task, current_user):
        raise HTTPException(status_code=403, detail="You cannot assign tasks outside your scope")

    staff = db.query(User).filter(
        and_(User.id == request.assigned_to, User.resort_id == resort_id)
    ).first()

    if not staff:
        raise HTTPException(status_code=404, detail="Staff user not found")
    if staff.role != "STAFF" or staff.department_id != task.department_id:
        raise HTTPException(status_code=400, detail="Task must be assigned to staff in its department")

    old_assignee = task.assignee.name if task.assignee else "Unassigned"
    task.assigned_to = staff.id
    if task.status in {"PENDING", "ESCALATED"}:
        task.status = "ASSIGNED"

    log = ActivityLog(
        resort_id=resort_id,
        user_id=current_user.id,
        user_name=current_user.name,
        user_role=current_user.role,
        action_type="TASK_ASSIGNED",
        entity_type="task",
        entity_id=task.id,
        description=f"{current_user.name} assigned task '{task.title}' to {staff.name} (was: {old_assignee})",
        details_json={"task_id": task.id, "assigned_to": staff.id, "staff_name": staff.name}
    )
    db.add(log)
    db.commit()

    return {
        "success": True,
        "task_id": task.id,
        "assigned_to": staff.id,
        "assignee_name": staff.name,
        "status": task.status,
        "message": f"Task assigned to {staff.name}"
    }


@router.patch("/{task_id}/status")
def update_task_status(
    task_id: int,
    request: TaskStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update task status (PENDING, IN_PROGRESS, COMPLETED, CANCELLED).
    Staff updates their assigned tasks.
    """
    resort_id = current_user.resort_id

    task = db.query(Task).filter(
        and_(Task.id == task_id, Task.resort_id == resort_id)
    ).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if current_user.role == "STAFF" and task.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="You can only update your assigned tasks")
    if current_user.role == "DEPARTMENT_HEAD" and task.department_id != get_department_head_department_id(current_user):
        raise HTTPException(status_code=403, detail="You can only update tasks in your department")
    if current_user.role not in {"MANAGER", "STAFF", "DEPARTMENT_HEAD"}:
        raise HTTPException(status_code=403, detail="Role cannot update operational tasks")

    old_status = task.status
    task.status = request.status.upper()
    if task.status not in TASK_STATUSES:
        raise HTTPException(status_code=400, detail=f"Unsupported task status: {task.status}")
    if task.status not in TASK_TRANSITIONS.get(old_status, set()):
        raise HTTPException(status_code=400, detail=f"Cannot move task from {old_status} to {task.status}")
    if task.status == "BLOCKED" and not request.blocker_reason:
        raise HTTPException(status_code=400, detail="blocker_reason is required when blocking a task")
    if request.blocker_reason:
        task.blocker_reason = request.blocker_reason

    if task.status == "COMPLETED" and old_status != "COMPLETED":
        task.completed_at = datetime.utcnow()
        for guest_request in task.guest_requests:
            if guest_request.status != "COMPLETED":
                guest_request.status = "COMPLETED"
                guest_request.completed_at = task.completed_at

    log = ActivityLog(
        resort_id=resort_id,
        user_id=current_user.id,
        user_name=current_user.name,
        user_role=current_user.role,
        action_type="TASK_STATUS_UPDATED",
        entity_type="task",
        entity_id=task.id,
        description=f"{current_user.name} updated task '{task.title}' status to {task.status}",
        details_json={"task_id": task.id, "old_status": old_status, "new_status": task.status}
    )
    db.add(log)
    db.commit()

    return {
        "success": True,
        "task_id": task.id,
        "status": task.status,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "message": f"Task status updated to {task.status}"
    }


@router.patch("/{task_id}/escalate")
def escalate_task(
    task_id: int,
    request: TaskEscalateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(
        and_(Task.id == task_id, Task.resort_id == current_user.resort_id)
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if current_user.role == "STAFF" and task.assigned_to != current_user.id:
        raise HTTPException(status_code=403, detail="You can only escalate your assigned tasks")
    if current_user.role == "DEPARTMENT_HEAD" and task.department_id != get_department_head_department_id(current_user):
        raise HTTPException(status_code=403, detail="You can only escalate tasks in your department")
    if current_user.role not in {"MANAGER", "STAFF", "DEPARTMENT_HEAD"}:
        raise HTTPException(status_code=403, detail="Role cannot escalate tasks")
    if task.status not in {"BLOCKED", "IN_PROGRESS", "ESCALATED"}:
        raise HTTPException(status_code=400, detail="Only blocked or active tasks can be escalated")

    target = None
    if current_user.role == "DEPARTMENT_HEAD":
        if request.escalate_to_user_id:
            target = db.query(User).filter(
                User.id == request.escalate_to_user_id,
                User.resort_id == current_user.resort_id,
                User.role == "MANAGER",
            ).first()
            if not target:
                raise HTTPException(status_code=400, detail="Department Heads can only escalate to a manager")
        else:
            target = db.query(User).filter(
                User.resort_id == current_user.resort_id,
                User.role == "MANAGER",
            ).first()
            if not target:
                raise HTTPException(status_code=409, detail="No manager is available to receive this escalation")
    elif request.escalate_to_user_id:
        target = db.query(User).filter(
            and_(User.id == request.escalate_to_user_id, User.resort_id == current_user.resort_id)
        ).first()
        if not target or target.role not in {"DEPARTMENT_HEAD", "MANAGER"}:
            raise HTTPException(status_code=400, detail="Escalation target must be a department head or manager")
    else:
        target = db.query(User).filter(
            and_(User.resort_id == current_user.resort_id, User.role == "MANAGER")
        ).first()
        if not target:
            target = db.query(User).filter(
                and_(User.resort_id == current_user.resort_id, User.department_id == task.department_id,
                     User.role == "DEPARTMENT_HEAD")
            ).first()

    old_status = task.status
    task.blocker_reason = request.blocker_reason
    task.escalated_to_user_id = target.id if target else None
    task.escalated_at = datetime.utcnow()
    task.status = "ESCALATED"
    db.add(ActivityLog(
        resort_id=current_user.resort_id,
        user_id=current_user.id,
        user_name=current_user.name,
        user_role=current_user.role,
        action_type="TASK_ESCALATED",
        entity_type="task",
        entity_id=task.id,
        description=f"{current_user.name} escalated '{task.title}': {request.blocker_reason}",
        details_json={"old_status": old_status, "blocker_reason": request.blocker_reason,
                      "escalated_to_user_id": task.escalated_to_user_id}
    ))
    db.commit()
    db.refresh(task)
    return serialize_task(task)

