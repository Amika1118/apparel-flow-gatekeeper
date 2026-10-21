from datetime import timezone, datetime
from typing import List, Tuple

from altair import Order
from sqlalchemy.orm import Session

from app.errors import NotFoundError, InvalidStateError, ValidationFailure, GatekeeperViolation
from app.models import OrderStatus, CuttingOrder, VerificationItem, VerificationLog, Decision, User
from app.schemas import GateSummary, CountSubmission
from app.services.state_machine import apply_transition
from app.services.traffic_light import evaluate_order, evaluate
from app.services.wastage import expected_fabric, wastage_pct

COUNTING_STATES = [OrderStatus.PENDING_VERIFICATION, OrderStatus.COUNT_QC]

def load_order_for_update(db: Session, order_id: int) -> CuttingOrder:
    order = (
        db.query(CuttingOrder)
        .filter(CuttingOrder.id == order_id)
        .with_for_update()
        .first()
    )

    if not order:
        raise NotFoundError("order not found")

    return order


def list_pending(db: Session) -> List[CuttingOrder]:
    return (
        db.query(CuttingOrder)
        .filter(CuttingOrder.status.in_(COUNTING_STATES))
        .order_by(CuttingOrder.id.asc())
        .all()
    )


def get_for_verification(db: Session, order_id: int) -> Tuple[CuttingOrder, GateSummary]:
    """Retrieves order details and gate summary evaluation for verification."""
    order = db.query(CuttingOrder).filter(CuttingOrder.id == order_id).first()

    if not order:
        raise NotFoundError("order not found")

    if order.status not in COUNTING_STATES:
        raise InvalidStateError("order is not awaiting verification")

    summary, _ = evaluate_order(order.items)

    return order, summary


def record_counts(db: Session, order_id : int, submission : CountSubmission) -> Tuple[List[VerificationItem], GateSummary]:
    order = load_order_for_update(db, order_id)

    if order.status not in COUNTING_STATES:
        raise InvalidStateError("counts are frozen")

    valid_ids = {item.component_id for item in order.items}
    submission_ids = (entry.component_id for entry in submission.entries)
    unknown = submission_ids - valid_ids

    if unknown:
        raise ValidationFailure(
            message="components do not belong to this order",
            details={"unknown_component_ids" : list(unknown)},
        )

    try:
        items_by_comp_id = {item.component_id: item for item in order.items}

        for entry in submission.counts:
            item = items_by_comp_id[entry.component_id]
            item.actual_qty = entry.actual_qty
            item.status = evaluate(item.expected_qty, item.actual_qty)

        if order.status == OrderStatus.PENDING_VERIFICATION:
            apply_transition(order, OrderStatus.COUNT_QC)

        summary, _ = evaluate_order(order.items)
        db.commit()
        return order.items, summary
    except Exception:
        db.rollback()
        raise


def approve(db: Session, order_id: int, verifier: User) -> CuttingOrder:
    """Approves order verification after checking gatekeeper rule and calculating fabric wastage."""
    order = load_order_for_update(db, order_id)

    # STEP 1: Verify valid state
    if order.status != OrderStatus.COUNT_QC:
        raise InvalidStateError("order is not ready for approval")

    # STEP 2: Gatekeeper evaluation check
    summary, blocking = evaluate_order(order.items)
    if not summary.can_approve:
        raise GatekeeperViolation(
            message="batch cannot be approved: shortage or uncounted components",
            details={"blocking_items": blocking},
        )

    # STEP 3: Fabric wastage calculation
    expected = expected_fabric(order.target_qty, order.recipe.std_fabric_yards)
    pct = wastage_pct(order.actual_fabric_yds, expected)

    # STEP 4: Persist changes and create verification log entry
    try:
        for item in order.items:
            item.status = evaluate(item.expected_qty, item.actual_qty)

        apply_transition(order, OrderStatus.VERIFIED)

        log_entry = VerificationLog(
            order_id=order.id,
            verifier_id=verifier.id,
            decision=Decision.VERIFIED,
            wastage_pct=pct,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(log_entry)

        db.commit()
        db.refresh(order)
        return order
    except Exception:
        db.rollback()
        raise


def reject(
    db: Session, order_id: int, verifier: User, note: str
) -> CuttingOrder:
    """Rejects an order, setting status to REJECTED with a required reason note."""
    order = load_order_for_update(db, order_id)

    if order.status != OrderStatus.COUNT_QC:
        raise InvalidStateError("order is not at the counting stage")

    clean_note = note.strip() if note else ""
    if not clean_note:
        raise ValidationFailure("rejection reason required")

    try:
        apply_transition(order, OrderStatus.REJECTED)

        log_entry = VerificationLog(
            order_id=order.id,
            verifier_id=verifier.id,
            decision=Decision.REJECTED,
            rejection_note=clean_note,
            wastage_pct=None,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(log_entry)

        db.commit()
        db.refresh(order)
        return order
    except Exception:
        db.rollback()
        raise