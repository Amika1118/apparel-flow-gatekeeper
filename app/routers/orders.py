from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import User, Role
from app.schemas import OrderCreate, OrderOut
from app.services.order_service import (
    create_order,
    get_order,
    list_orders_for_supervisor,
    submit_for_verification,
)

router = APIRouter(prefix="/orders", tags=["Orders"])

# Every route below requires cutting_supervisor role
SUPERVISOR_DEP = Depends(require_role([Role.CUTTING_SUPERVISOR]))


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_new_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = SUPERVISOR_DEP,
) -> OrderOut:
    """Creates a new cutting order and its verification items for the supervisor."""
    order = create_order(db, user, payload)
    return OrderOut.model_validate(order)


@router.get("", response_model=List[OrderOut])
def list_orders(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = SUPERVISOR_DEP,
) -> List[OrderOut]:
    """Lists all cutting orders created by the authenticated supervisor."""
    orders = list_orders_for_supervisor(db, user)
    return [OrderOut.model_validate(o) for o in orders]


@router.get("/{order_id}", response_model=OrderOut)
def get_single_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = SUPERVISOR_DEP,
) -> OrderOut:
    """Retrieves details for a specific cutting order owned by the supervisor."""
    order = get_order(db, order_id, user)
    return OrderOut.model_validate(order)


@router.post("/{order_id}/submit", response_model=OrderOut)
def submit_order_for_verification(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = SUPERVISOR_DEP,
) -> OrderOut:
    """Submits a cutting order for quality verification."""
    order = submit_for_verification(db, order_id, user)
    return OrderOut.model_validate(order)