from typing import Any, Dict, List, Optional, Tuple, Union

from app.models import TrafficFlag, VerificationItem
from app.schemas import GateSummary

def evaluate(expected: int, actual: Optional[int]) -> Union[TrafficFlag, str]:
    """Evaluates the traffic flag based on expected and actual quantities."""
    if actual is None:
        return "uncounted"
    if actual == expected:
        return TrafficFlag.GREEN
    if actual > expected:
        return TrafficFlag.YELLOW
    return TrafficFlag.RED


def variance(expected: int, actual: Optional[int]) -> Optional[int]:
    """Calculates variance between actual and expected quantities."""
    if actual is None:
        return None
    return actual - expected


def evaluate_order(
    items: List[VerificationItem],
) -> Tuple[GateSummary, List[Dict[str, Any]]]:
    """Evaluates an order's verification items to generate a gate summary and blocking issues."""
    green = 0
    yellow = 0
    red = 0
    uncounted = 0
    blocking: List[Dict[str, Any]] = []

    for item in items:
        # Recompute from raw numbers; never trust stored flag
        flag = evaluate(item.expected_qty, item.actual_qty)

        comp_name = item.component.component_name if item.component else "Unknown"

        if flag == "uncounted":
            uncounted += 1
            blocking.append(
                {
                    "component": comp_name,
                    "expected": item.expected_qty,
                    "actual": None,
                    "flag": "UNCOUNTED",
                }
            )
        elif flag == TrafficFlag.RED:
            red += 1
            actual_val = item.actual_qty if item.actual_qty is not None else 0
            blocking.append(
                {
                    "component": comp_name,
                    "expected": item.expected_qty,
                    "actual": actual_val,
                    "flag": "RED",
                    "shortfall": item.expected_qty - actual_val,
                }
            )
        elif flag == TrafficFlag.YELLOW:
            yellow += 1
        else:
            green += 1

    can_approve = (red == 0) and (uncounted == 0)
    summary = GateSummary(
        green=green,
        yellow=yellow,
        red=red,
        uncounted=uncounted,
        can_approve=can_approve,
    )

    return summary, blocking