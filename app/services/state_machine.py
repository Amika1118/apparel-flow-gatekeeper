from typing import Dict, List

from app.errors import InvalidStateError
from app.models import OrderStatus, CuttingOrder

ALLOWED_TRANSACTIONS : Dict[OrderStatus, List[OrderStatus]] = {
    OrderStatus.CUTTING_IN_PROGRESS : [OrderStatus.PENDING_VERIFICATION],
    OrderStatus.PENDING_VERIFICATION : [OrderStatus.COUNT_QC],
    OrderStatus.COUNT_QC : [OrderStatus.VERIFIED, OrderStatus.REJECTED],
    OrderStatus.REJECTED : [OrderStatus.PENDING_VERIFICATION],
    OrderStatus.VERIFIED : [OrderStatus.IN_SEWING],
    OrderStatus.IN_SEWING : [],

}

def assert_transaction(order: CuttingOrder, new_status: OrderStatus) -> None:
    allowed = ALLOWED_TRANSACTIONS.get(order.status, [])

    if new_status not in allowed:

        current_status_val = order.status.value if isinstance(order.status, OrderStatus) else str(order.status)
        new_status_val = new_status.value if isinstance(new_status, OrderStatus) else str(new_status)

        raise InvalidStateError(
            message=f"cannot move from {current_status_val} to {new_status_val}",
            details={"current": current_status_val, "attempted": new_status_val},
        )

def apply_transition(order: CuttingOrder, new_status: OrderStatus) -> None:
    """Applies a valid status transition to the given cutting order.

        RULE: This function is the single point of truth and the ONLY place in
        the codebase allowed to mutate order.status.
        """
    assert_transaction(order, new_status)
    order.status = new_status