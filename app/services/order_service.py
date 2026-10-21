from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import (
    CuttingOrder,
    Decision,
    OrderStatus,
    Recipe,
    User,
    VerificationItem,
    VerificationLog,
)
from app.schemas import OrderCreate
from app.services.state_machine import apply_transition


def generate_order_no(db: Session) -> str:
    """Generates a unique sequential cutting order number formatted as 'CO-YYYY-XXXX'."""
    year = str(datetime.now(timezone.utc).year)
    prefix = f"CO-{year}-"

    latest_order = (
        db.query(CuttingOrder)
        .filter(CuttingOrder.order_no.like(f"{prefix}%"))
        .order_by(CuttingOrder.order_no.desc())
        .first()
    )

    if not latest_order:
        next_number = 1
    else:
        last_num_str = latest_order.order_no.split("-")[-1]
        next_number = int(last_num_str) + 1

    return f"CO-{year}-{next_number:04d}"


def find_own_order(db: Session, order_id: int, user: User) -> CuttingOrder:
    """Retrieves an order belonging to the user. Raises NotFoundError if not found or unauthorized."""
    order = (
        db.query(CuttingOrder)
        .filter(CuttingOrder.id == order_id, CuttingOrder.created_by == user.id)
        .first()
    )

    if not order:
        raise NotFoundError("order not found")

    return order


def create_order(db: Session, user: User, payload: OrderCreate) -> CuttingOrder:
    """Creates a new cutting order along with its associated verification items."""
    recipe = db.query(Recipe).filter(Recipe.id == payload.recipe_id).first()
    if not recipe:
        raise NotFoundError("recipe not found")

    try:
        order = CuttingOrder(
            order_no=generate_order_no(db),
            recipe_id=recipe.id,
            target_qty=payload.target_qty,
            fabric_roll_id=payload.fabric_roll_id,
            actual_fabric_yds=payload.actual_fabric_yds,
            status=OrderStatus.CUTTING_IN_PROGRESS,
            created_by=user.id,
        )
        db.add(order)
        db.flush()

        for component in recipe.components:
            item = VerificationItem(
                order_id=order.id,
                component_id=component.id,
                expected_qty=payload.target_qty * component.pieces_per_garment,
                actual_qty=None,
                status=None,
            )
            db.add(item)

        db.commit()
        db.refresh(order)
        return order
    except Exception:
        db.rollback()
        raise


def submit_for_verification(db: Session, order_id: int, user: User) -> CuttingOrder:
    """Submits an order for verification, resetting item counts if previously rejected."""
    order = find_own_order(db, order_id, user)
    was_rejected = order.status == OrderStatus.REJECTED

    apply_transition(order, OrderStatus.PENDING_VERIFICATION)

    if was_rejected:
        for item in order.items:
            item.actual_qty = None
            item.status = None

    db.commit()
    db.refresh(order)
    return order


def _attach_latest_rejection_note(db: Session, order: CuttingOrder) -> None:
    """Helper to attach the latest rejection note to a rejected order."""
    if order.status == OrderStatus.REJECTED:
        log = (
            db.query(VerificationLog)
            .filter(
                VerificationLog.order_id == order.id,
                VerificationLog.decision == Decision.REJECTED,
            )
            .order_by(VerificationLog.timestamp.desc())
            .first()
        )
        setattr(order, "latest_rejection_note", log.rejection_note if log else None)


def list_orders_for_supervisor(db: Session, user: User) -> List[CuttingOrder]:
    """Lists all cutting orders created by the supervisor, newest first."""
    orders = (
        db.query(CuttingOrder)
        .filter(CuttingOrder.created_by == user.id)
        .order_by(CuttingOrder.id.desc())
        .all()
    )

    for order in orders:
        _attach_latest_rejection_note(db, order)

    return orders


def get_order(db: Session, order_id: int, user: User) -> CuttingOrder:
    """Retrieves details of a specific cutting order created by the user."""
    order = find_own_order(db, order_id, user)
    _attach_latest_rejection_note(db, order)
    return order