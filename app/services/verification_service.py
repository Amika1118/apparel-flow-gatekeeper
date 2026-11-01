# app/services/verification_service.py
from datetime import datetime, timezone
from typing import List, Tuple

from sqlalchemy.orm import Session

from app.errors import (
    GatekeeperViolation,
    InvalidStateError,
    NotFoundError,
    ValidationFailure,
)
from app.models import (
    CuttingOrder,
    Decision,
    OrderStatus,
    User,
    VerificationItem,
    VerificationLog,
)
from app.schemas import CountSubmission, GateSummary
from app.services.state_machine import apply_transition
from app.services.traffic_light import evaluate, evaluate_order
from app.services.wastage import expected_fabric, wastage_pct

COUNTING_STATES = [OrderStatus.PENDING_VERIFICATION, OrderStatus.COUNT_QC]


def load_order_for_update(db: Session, order_id: int) -> CuttingOrder:
    """Retrieves a cutting order and locks the row for update."""
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
    """Lists all orders awaiting verification in FIFO order (oldest first)."""
    return (
        db.query(CuttingOrder)
        .filter(CuttingOrder.status.in_(COUNTING_STATES))
        .order_by(CuttingOrder.id.asc())
        .all()
    )


def get_for_verification(
    db: Session, order_id: int
) -> Tuple[CuttingOrder, GateSummary]:
    """Retrieves order details and gate summary evaluation for verification."""
    order = db.query(CuttingOrder).filter(CuttingOrder.id == order_id).first()

    if not order:
        raise NotFoundError("order not found")

    if order.status not in COUNTING_STATES:
        raise InvalidStateError("order is not awaiting verification")

    summary, _ = evaluate_order(order.items)
    return order, summary


def record_counts(
    db: Session, order_id: int, submission: CountSubmission
) -> Tuple[List[VerificationItem], GateSummary]:
    """Records piece counts submitted by verifiers and updates order state with concurrency safeguards."""
    order = load_order_for_update(db, order_id)

    if order.status not in COUNTING_STATES:
        raise InvalidStateError("counts are frozen")

    valid_ids = {item.component_id for item in order.items}
    submission_ids = {entry.component_id for entry in submission.counts}
    unknown = submission_ids - valid_ids

    if unknown:
        raise ValidationFailure(
            message="components do not belong to this order",
            details={"unknown_component_ids": list(unknown)},
        )

    try:
        items_by_comp_id = {item.component_id: item for item in order.items}

        for entry in submission.counts:
            item = items_by_comp_id[entry.component_id]
            item.actual_qty = entry.actual_qty
            item.status = evaluate(item.expected_qty, item.actual_qty)

        if order.status == OrderStatus.PENDING_VERIFICATION:
            rows_changed = (
                db.query(CuttingOrder)
                .filter(
                    CuttingOrder.id == order.id,
                    CuttingOrder.status == OrderStatus.PENDING_VERIFICATION,
                )
                .update(
                    {"status": OrderStatus.COUNT_QC}, synchronize_session=False
                )
            )
            if rows_changed != 1:
                raise InvalidStateError("someone else changed this order")
            order.status = OrderStatus.COUNT_QC

        summary, _ = evaluate_order(order.items)
        db.commit()
        return order.items, summary
    except Exception:
        db.rollback()
        raise


def approve(db: Session, order_id: int, verifier: User) -> CuttingOrder:
    """Approves order verification with optimistic concurrency control and wastage calculations."""
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

    # STEP 4: Persist changes with atomic status update check
    try:
        for item in order.items:
            item.status = evaluate(item.expected_qty, item.actual_qty)

        rows_changed = (
            db.query(CuttingOrder)
            .filter(
                CuttingOrder.id == order.id,
                CuttingOrder.status == OrderStatus.COUNT_QC,
            )
            .update({"status": OrderStatus.VERIFIED}, synchronize_session=False)
        )
        if rows_changed != 1:
            raise InvalidStateError("someone else changed this order")

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
    """Rejects an order with atomic status update check and required reason note."""
    order = load_order_for_update(db, order_id)

    if order.status != OrderStatus.COUNT_QC:
        raise InvalidStateError("order is not at the counting stage")

    clean_note = note.strip() if note else ""
    if not clean_note:
        raise ValidationFailure("rejection reason required")

    try:
        rows_changed = (
            db.query(CuttingOrder)
            .filter(
                CuttingOrder.id == order.id,
                CuttingOrder.status == OrderStatus.COUNT_QC,
            )
            .update({"status": OrderStatus.REJECTED}, synchronize_session=False)
        )
        if rows_changed != 1:
            raise InvalidStateError("someone else changed this order")

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