from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import User, Role
from app.schemas import OrderOut, SewingBatchOut, SewingQueueRow
from app.services.sewing_service import (
    get_batch_detail,
    get_queue,
    start_assembly,
)

router = APIRouter(tags=["Sewing"])

# Every route below requires sewing_supervisor role
SEWING_SUPERVISOR_DEP = Depends(require_role(Role.SEWING_SUPERVISOR))


@router.get("/sewing/queue", response_model=List[SewingQueueRow])
def get_sewing_queue(
    db: Session = Depends(get_db),
    _: None = SEWING_SUPERVISOR_DEP,
) -> List[SewingQueueRow]:
    """Retrieves the list of verified batches ready for sewing assembly."""
    return get_queue(db)


@router.get("/sewing/{order_id}", response_model=SewingBatchOut)
def get_sewing_batch_details(
    order_id: int,
    db: Session = Depends(get_db),
    _: None = SEWING_SUPERVISOR_DEP,
) -> SewingBatchOut:
    """Retrieves detailed information for a verified sewing batch, including variances and wastage cap checks."""
    return get_batch_detail(db, order_id)


@router.post("/sewing/{order_id}/start", response_model=OrderOut)
def start_sewing_assembly(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = SEWING_SUPERVISOR_DEP,
) -> OrderOut:
    """Transitions a verified batch to IN_SEWING assembly status, removing it from the queue."""
    order = start_assembly(db, order_id, user)
    return OrderOut.model_validate(order)