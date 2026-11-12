# tests/test_verification.py
import pytest
from app.models import OrderStatus, Role, VerificationLog
from tests.conftest import get_user, make_order, auth_headers


def test_valid_approval(client, db):
    # ARRANGE
    order = make_order(db, "REC-BL01", 10, OrderStatus.PENDING_VERIFICATION)
    headers = auth_headers(client, Role.CUTTING_VERIFIER)

    # ACT
    response = client.post(f"/api/orders/{order.id}/verify", headers=headers)

    # ASSERT
    assert response.status_code == 200
    db.expire_all()
    reloaded_order = db.get(type(order), order.id)
    assert reloaded_order.status == OrderStatus.VERIFIED

    logs = db.query(VerificationLog).filter(VerificationLog.order_id == order.id).all()
    assert len(logs) == 1
    assert logs[0].decision == OrderStatus.VERIFIED

    verifier = get_user(db, Role.CUTTING_VERIFIER)
    assert logs[0].verifier_id == verifier.id
    assert logs[0].wastage_pct is not None


def test_shortage_hard_stop(client, db):
    order = make_order(
        db,
        "REC-BL01",
        10,
        OrderStatus.PENDING_VERIFICATION,
        counts={"Sleeves (Left & Right)": 18},
    )
    headers = auth_headers(client, Role.CUTTING_VERIFIER)
    response = client.post(f"/api/orders/{order.id}/verify", headers=headers)

    assert response.status_code == 422
    assert "Sleeves (Left & Right)" in response.text

    db.expire_all()
    reloaded_order = db.get(type(order), order.id)
    assert reloaded_order.status == OrderStatus.PENDING_VERIFICATION

    logs = db.query(VerificationLog).filter(VerificationLog.order_id == order.id).all()
    assert len(logs) == 0


def test_rejection_requires_note(client, db):
    order = make_order(
        db,
        "REC-BL01",
        10,
        OrderStatus.PENDING_VERIFICATION,
        counts={"Sleeves (Left & Right)": 18},
    )
    headers = auth_headers(client, Role.CUTTING_VERIFIER)

    for bad_note in ["", "   "]:
        response = client.post(
            f"/api/orders/{order.id}/reject",
            json={"note": bad_note},
            headers=headers,
        )
        assert response.status_code == 422

    db.expire_all()
    reloaded_order = db.get(type(order), order.id)
    assert reloaded_order.status == OrderStatus.PENDING_VERIFICATION

    logs = db.query(VerificationLog).filter(VerificationLog.order_id == order.id).all()
    assert len(logs) == 0

    response = client.post(
        f"/api/orders/{order.id}/reject",
        json={"note": "Shortage of 2 sleeves due to fabric tear"},
        headers=headers,
    )
    assert response.status_code == 200

    db.expire_all()
    reloaded_order = db.get(type(order), order.id)
    assert reloaded_order.status == OrderStatus.REJECTED

    logs = db.query(VerificationLog).filter(VerificationLog.order_id == order.id).all()
    assert len(logs) == 1
    assert logs[0].decision == OrderStatus.REJECTED
    assert logs[0].note == "Shortage of 2 sleeves due to fabric tear"


def test_rbac_violation(client, db):
    order = make_order(db, "REC-BL01", 10, OrderStatus.PENDING_VERIFICATION)

    for role in [Role.CUTTING_SUPERVISOR, Role.SEWING_SUPERVISOR]:
        headers = auth_headers(client, role)
        response = client.post(f"/api/orders/{order.id}/verify", headers=headers)
        assert response.status_code == 403

    db.expire_all()
    reloaded_order = db.get(type(order), order.id)
    assert reloaded_order.status == OrderStatus.PENDING_VERIFICATION

    response = client.post(f"/api/orders/{order.id}/verify")
    assert response.status_code == 401


def test_sewing_queue_isolation(client, db):
    o1 = make_order(db, "REC-BL01", 10, OrderStatus.CUTTING_IN_PROGRESS)
    o2 = make_order(db, "REC-BL01", 10, OrderStatus.PENDING_VERIFICATION)
    o3 = make_order(db, "REC-BL01", 10, OrderStatus.REJECTED)
    o4 = make_order(db, "REC-BL01", 10, OrderStatus.VERIFIED)

    verifier = get_user(db, Role.CUTTING_VERIFIER)
    log = VerificationLog(
        order_id=o4.id,
        verifier_id=verifier.id,
        decision=OrderStatus.VERIFIED,
        wastage_pct=2.5,
    )
    db.add(log)
    db.commit()

    headers = auth_headers(client, Role.SEWING_SUPERVISOR)

    response = client.get("/api/sewing/queue", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert [item["id"] for item in data] == [o4.id]

    response = client.get("/api/sewing/queue?status=REJECTED", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert [item["id"] for item in data] == [o4.id]

    response = client.get(f"/api/sewing/{o3.id}", headers=headers)
    assert response.status_code == 404