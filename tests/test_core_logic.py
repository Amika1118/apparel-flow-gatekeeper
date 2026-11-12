import pytest
from app.errors import InvalidStateError
from app.models import OrderStatus, Role, VerificationLog
from app.services.traffic_light import evaluate
from app.services.wastage import wastage_pct
from app.services.state_machine import apply_transition
from app.services.verification_service import approve
from tests.conftest import auth_headers, make_order


def test_traffic_light_values():
    assert evaluate(10, 10) == "GREEN"
    assert evaluate(10, 12) == "YELLOW"
    assert evaluate(10, 8) == "RED"
    assert evaluate(10, 0) == "RED"
    assert evaluate(10, None) == "uncounted"


def test_wastage_values():
    assert wastage_pct(96, 90) == 6.67
    assert wastage_pct(90, 90) == 0.00
    assert wastage_pct(85.5, 90) == -5.00


def test_illegal_transition(db):
    order = make_order(db, "REC-BL01", 10, OrderStatus.PENDING_VERIFICATION)
    with pytest.raises(InvalidStateError):
        apply_transition(order, OrderStatus.VERIFIED)


def test_approve_with_uncounted_item(client, db):
    order = make_order(db, "REC-BL01", 10, OrderStatus.PENDING_VERIFICATION)
    # Leave an item uncounted or nullify actual_qty
    for item in order.items:
        item.actual_qty = None
    db.commit()

    headers = auth_headers(client, Role.CUTTING_VERIFIER)
    response = client.post(f"/api/orders/{order.id}/verify", headers=headers)
    assert response.status_code == 422


def test_approve_twice(client, db):
    order = make_order(db, "REC-BL01", 10, OrderStatus.PENDING_VERIFICATION)
    # Ensure counts match expected
    for item in order.items:
        item.actual_qty = item.expected_qty
    db.commit()

    headers = auth_headers(client, Role.CUTTING_VERIFIER)

    # First approval succeeds
    response1 = client.post(f"/api/orders/{order.id}/verify", headers=headers)
    assert response1.status_code == 200

    # Second approval fails with conflict (409) due to state machine rule
    response2 = client.post(f"/api/orders/{order.id}/verify", headers=headers)
    assert response2.status_code == 409


@pytest.mark.parametrize("bad_qty", [0, -5, 12.5, "abc", None])
def test_order_validation_quantities(client, db, bad_qty):
    headers = auth_headers(client, Role.CUTTING_SUPERVISOR)
    payload = {
        "recipe_id": 1,
        "target_qty": bad_qty,
        "fabric_roll_id": "R-TEST",
        "actual_fabric_yds": 50.0,
        "items": [],
    }
    response = client.post("/api/orders", json=payload, headers=headers)
    assert response.status_code == 422


def test_order_validation_extra_field(client, db):
    headers = auth_headers(client, Role.CUTTING_SUPERVISOR)
    payload = {
        "recipe_id": 1,
        "target_qty": 10,
        "fabric_roll_id": "R-TEST",
        "actual_fabric_yds": 50.0,
        "items": [],
        "status": "VERIFIED",  # Extra/illegal field in creation payload
    }
    response = client.post("/api/orders", json=payload, headers=headers)
    assert response.status_code == 422


def test_resubmit_resets_counts(client, db):
    order = make_order(db, "REC-BL01", 10, OrderStatus.PENDING_VERIFICATION)
    verifier = auth_headers(client, Role.CUTTING_VERIFIER)
    supervisor = auth_headers(client, Role.CUTTING_SUPERVISOR)

    # Reject the order first
    reject_res = client.post(
        f"/api/orders/{order.id}/reject",
        json={"note": "Recut required due to flaws"},
        headers=verifier,
    )
    assert reject_res.status_code == 200

    # Resubmit the order
    submit_res = client.post(f"/api/orders/{order.id}/submit", headers=supervisor)
    assert submit_res.status_code == 200

    db.expire_all()
    reloaded_order = db.get(type(order), order.id)
    for item in reloaded_order.items:
        assert item.actual_qty is None