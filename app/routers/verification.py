# app/routers/verification.py
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import User, Role
from app.schemas import (
    CountResultOut,
    CountSubmission,
    OrderOut,
    RejectRequest,
)

from app.services.verification_service import (
    approve,
    get_for_verification,
    list_pending,
    record_counts,
    reject,
)

router = APIRouter(tags=["Verification"])

# Every route below requires cutting_verifier role
VERIFIER_DEP = Depends(require_role(Role.CUTTING_VERIFIER))


@router.get("/verification/pending", response_model=List[OrderOut])
def get_pending_verification_orders(
    db: Session = Depends(get_db),
    _: None = VERIFIER_DEP,
) -> List[OrderOut]:
    """Lists all cutting orders currently pending verification in FIFO order."""
    orders = list_pending(db)
    return [OrderOut.model_validate(o) for o in orders]


@router.get("/verification/{order_id}")
def get_verification_details(
    order_id: int,
    db: Session = Depends(get_db),
    _: None = VERIFIER_DEP,
):
    """Retrieves order details and gate summary evaluation for verification."""
    order, summary = get_for_verification(db, order_id)
    return {
        "order": OrderOut.model_validate(order),
        "summary": summary,
    }


@router.put("/verification/{order_id}/counts", response_model=CountResultOut)
def update_verification_counts(
    order_id: int,
    payload: CountSubmission,
    db: Session = Depends(get_db),
    _: None = VERIFIER_DEP,
) -> CountResultOut:
    """Records piece counts submitted by verifiers and returns updated item results and summary."""
    items, summary = record_counts(db, order_id, payload)
    return CountResultOut(items=items, summary=summary)


@router.post("/orders/{order_id}/verify", response_model=OrderOut)
def verify_and_approve_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = VERIFIER_DEP,
) -> OrderOut:
    """Approves a cutting order batch after validating gatekeeper criteria and calculating fabric wastage."""
    order = approve(db, order_id, user)
    return OrderOut.model_validate(order)


@router.post("/orders/{order_id}/reject", response_model=OrderOut)
def reject_order(
    order_id: int,
    payload: RejectRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = VERIFIER_DEP,
) -> OrderOut:
    """Rejects a cutting order with a required reason note, returning it for supervisor recutting."""
    order = reject(db, order_id, user, payload.note)
    return OrderOut.model_validate(order)