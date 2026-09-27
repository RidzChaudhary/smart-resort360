from fastapi import APIRouter, Depends
from fastapi import HTTPException
import logging
import os
from sqlalchemy.orm import Session

from app.database.connection import get_db, engine, Base
from app.database.seed import seed_database
from app.models import User
from app.utils.auth import require_role

router = APIRouter(prefix="/api/demo", tags=["Demo & Admin"])
logger = logging.getLogger(__name__)


def require_non_production_demo_mode():
    if os.getenv("APP_ENV", "development").strip().casefold() == "production":
        raise HTTPException(status_code=404, detail="Not found")

@router.post("/reset")
def reset_demo_data(
    current_user: User = Depends(require_role(["MANAGER"])),
    db: Session = Depends(get_db)
):
    """
    Reset the entire database to demo state.
    Wipes all data and reseeds with synthetic operational data.

    Manager-only endpoint.

    WARNING: This is destructive and should only be used for demo/development.
    """
    require_non_production_demo_mode()
    try:
        # Close current session
        db.close()

        # Run seed
        seed_database(reset_schema=True)
        
        # Also seed Phase 1 demo data if default resort exists
        from app.models import Resort
        from app.services.phase1_demo_seed import seed_phase1_demo
        resort = db.query(Resort).first()
        if resort:
            seed_phase1_demo(db, resort.id)

        return {
            "success": True,
            "message": "Database successfully reset to demo state with synthetic operational data."
        }
    except Exception as exc:
        logger.exception("Demo reset failed")
        raise HTTPException(status_code=500, detail="Demo reset failed") from exc


@router.post("/seed-phase1")
def seed_phase1_endpoint(
    current_user: User = Depends(require_role(["MANAGER"])),
    db: Session = Depends(get_db)
):
    """
    Seed Phase 1 demo data (Resort Locations and Sunset Pool BBQ event).
    """
    require_non_production_demo_mode()
    try:
        from app.services.phase1_demo_seed import seed_phase1_demo
        resort_id = current_user.resort_id or 1
        result = seed_phase1_demo(db, resort_id)
        return {
            "success": True,
            "result": result,
            "message": "Phase 1 demo locations and events successfully seeded."
        }
    except Exception as exc:
        logger.exception("Phase 1 demo seed failed")
        raise HTTPException(status_code=500, detail="Demo seed failed") from exc

