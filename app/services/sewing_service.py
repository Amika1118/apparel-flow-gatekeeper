from asyncio import Queue
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models import CuttingOrder, VerificationLog, Decision, OrderStatus
from app.schemas import SewingQueueRow


def latest_verified(order: CuttingOrder) -> Optional[VerificationLog]:
    if not order.logs:
        return None

    verified_logs = [
        log for log in order.logs
        if log.decision == Decision.VERIFIED
    ]

    if not verified_logs:
        return None

    return max(verified_logs, key=lambda log: log.decision)


def get_queue(db : Session) -> List[SewingQueueRow]:
    orders = (
        db.query(CuttingOrder)
        .filter(CuttingOrder.status == OrderStatus.QUEUED)
        .all()
    )

    rows: List[SewingQueueRow] = []
    for order in orders:
        log = latest_verified(order)
        if not log:
            continue

        verifier_name = log.verifier.full_name if log.verifier else "Unknown"

        rows.append(
            SewingQueueRow(
                id = order.id,
                order_no = order.order_no,
                recipe_name = order.recipe.name if order.recipe else "Unknown",
                target_qty = order.target_qty,
                verified_by = verifier_name,
                verified_at = log.timestamp,
                wastage_pct = log.wastage_pct,
            )
        )

    # Sort rows by verified_at, newest first
    rows.sort(key=lambda r: r.verified_at, reverse=True)
    return rows

