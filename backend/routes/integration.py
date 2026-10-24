from fastapi import APIRouter

from ..schemas import SyncInput, SyncOut
from ..services.integration_service import simulate_orbyte_sync
from .workflow import DB

router = APIRouter(prefix="/api/integration", tags=["Orbyte integration (simulated)"])


@router.post("/orbyte-sync", response_model=SyncOut)
def orbyte_sync(db: DB, data: SyncInput = SyncInput()):
    """Prepare an Orbyte-shaped payload, log it, and return it. No external calls."""
    return simulate_orbyte_sync(db, data)
