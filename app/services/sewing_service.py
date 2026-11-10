from typing import List, Optional

from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import (
    CuttingOrder,
    Decision,
    OrderStatus,
    User,
    VerificationLog,
)
from app.schemas import ItemOut, SewingBatchOut, SewingQueueRow, VerificationLogOut
from app.services.state_machine import apply_transition
from app.services.traffic_light import variance
from app.services.wastage import exceeds_cap


def latest_verified_log(order: CuttingOrder) -> Optional[VerificationLog]:
    """Retrieves the newest verification log for an order where the decision was VERIFIED."""
    if not order.logs:
        return None

    verified_logs = [
        log for log in order.logs
        if log.decision == Decision.VERIFIED
    ]
    if not verified_logs:
        return None

    return max(verified_logs, key=lambda l: l.timestamp)


def get_queue(db: Session) -> List[SewingQueueRow]:
    """Retrieves all verified orders ready for sewing assembly queue, sorted newest first."""
    orders = (
        db.query(CuttingOrder)
        .filter(CuttingOrder.status == OrderStatus.VERIFIED)
        .all()
    )

    rows: List[SewingQueueRow] = []
    for order in orders:
        log = latest_verified_log(order)
        if not log:
            continue

        verifier_name = log.verifier.full_name if log.verifier else "Unknown"

        rows.append(
            SewingQueueRow(
                id=order.id,
                order_no=order.order_no,
                recipe_name=order.recipe.name if order.recipe else "Unknown",
                target_qty=order.target_qty,
                verified_by=verifier_name,
                verified_at=log.timestamp,
                wastage_pct=log.wastage_pct,
            )
        )

    # Sort rows by verified_at, newest first
    rows.sort(key=lambda r: r.verified_at, reverse=True)
    return rows


def find_verified_order(db: Session, order_id: int) -> CuttingOrder:
    """Finds a cutting order that is in VERIFIED status. Raises NotFoundError if missing or unverified."""
    order = (
        db.query(CuttingOrder)
        .filter(CuttingOrder.id == order_id, CuttingOrder.status == OrderStatus.VERIFIED)
        .first()
    )

    if not order:
        raise NotFoundError("batch not found")

    return order


def get_batch_detail(db: Session, order_id: int) -> SewingBatchOut:
    """Retrieves detailed batch information including items with variance and cap checks for sewing."""
    order = find_verified_order(db, order_id)
    log = latest_verified_log(order)

    item_outs = []
    for item in order.items:
        comp_name = item.component.component_name if item.component else "Unknown"
        v = variance(item.expected_qty, item.actual_qty)
        item_outs.append(
            ItemOut(
                component_id=item.component_id,
                component_name=comp_name,
                expected_qty=item.expected_qty,
                actual_qty=item.actual_qty,
                variance=v,
            )
        )

    wastage_percentage = log.wastage_pct if log and log.wastage_pct is not None else order.actual_fabric_yds  # fallback if needed
    cap = order.recipe.wastage_cap if order.recipe else 0
    is_over_cap = exceeds_cap(log.wastage_pct, cap) if log and log.wastage_pct is not None else False

    return SewingBatchOut(
        id=order.id,
        order_no=order.order_no,
        recipe_name=order.recipe.name if order.recipe else "Unknown",
        target_qty=order.target_qty,
        items=item_outs,
        log=VerificationLogOut(
            decision=log.decision.value if log else "",
            verifier_name=log.verifier.full_name if log and log.verifier else "Unknown",
            timestamp=log.timestamp if log else None,
            wastage_pct=log.wastage_pct if log else 0,
            rejection_note=log.rejection_note if log else None,
        ),
        wastage_pct=log.wastage_pct if log else 0,
        wastage_cap=cap,
        over_cap=is_over_cap,
    )


def start_assembly(db: Session, order_id: int, user: User) -> CuttingOrder:
    """Transitions a verified batch to sewing assembly, removing it from the active verification queue."""
    order = find_verified_order(db, order_id)

    try:
        apply_transition(order, OrderStatus.IN_SEWING)
        db.commit()
        db.refresh(order)
        return order
    except Exception:
        db.rollback()
        raise