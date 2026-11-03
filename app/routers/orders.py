from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from streamlit import status
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import User, Role
from app.schemas import OrderOut, OrderCreate
from app.services.order_service import create_order, list_orders_for_supervisor, get_order, submit_for_verification

router = APIRouter(prefix="/orders", tags=["orders"])

SUPERVISOR_DEP = Depends(require_role(Role.CUTTING_SUPERVISOR))

@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_new_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = SUPERVISOR_DEP,
) -> OrderOut:
    order = create_order(db, user, payload)
    return OrderOut.model_validate(order)


@router.get("", response_model=List[OrderOut])
def list_orders(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = SUPERVISOR_DEP,
) -> List[OrderOut]:
    orders = list_orders_for_supervisor(db, user)
    return [OrderOut.model_validate(o) for o in orders]


@router.get("/{order_id}", response_model=OrderOut)
def get_single_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = SUPERVISOR_DEP,
) -> OrderOut:
    order = get_order(db, order_id, user)
    return OrderOut.model_validate(order)


@router.post("/{order_id}/submit", response_model=OrderOut)
def submit_order_for_verification(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _: None = SUPERVISOR_DEP,
) -> OrderOut:
    order = submit_for_verification(db, order_id, user)
    return OrderOut.model_validate(order)