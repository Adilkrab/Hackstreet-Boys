"""API integration tests against an isolated SQLite file; never touches demo data."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

from src.backend.core import Base, Product
from src.backend.database import get_db
from src.backend.schemas import ReviewInput
from src.backend.services.automation import review_request
from src.backend.models import AuditLog, StockAdjustmentRequest
from src.backend.main import app


@pytest.fixture
def setup(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.sqlite3'}",
                           connect_args={"check_same_thread": False, "timeout": 15})

    @event.listens_for(engine, "connect")
    def configure(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=15000")

    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions.begin() as db:
        db.add(Product(id=1, sku="TEST-MILO", name="Milo 1kg", system_quantity=20,
                       unit_price=Decimal("24.90"), low_stock_threshold=5))
    def override():
        with sessions() as db:
            yield db
    app.dependency_overrides[get_db] = override
    # Deliberately do not enter the host's lifespan: tests create their own schema.
    client = TestClient(app)
    yield client, sessions, engine
    client.close()
    app.dependency_overrides.clear()
    engine.dispose()


def submit(client, count=15):
    return client.post("/api/workflow/stock-count", json={
        "product_id": 1, "physical_counted_qty": count,
        "submitted_by": "Stock clerk", "reason": "Shelf count",
    })


def review(client, request_id, action="APPROVE"):
    return client.post(f"/api/workflow/approvals/{request_id}/review", json={
        "action": action, "manager_name": "Store manager", "notes": "Verified",
    })


def quantity(sessions):
    with sessions() as db:
        return db.get(Product, 1).system_quantity


def test_minor_auto_approval(setup):
    client, sessions, _ = setup
    result = submit(client, 19)
    assert result.status_code == 201
    assert result.json()["status"] == "AUTO_APPROVED"
    assert result.json()["discrepancy_delta"] == -1
    assert Decimal(result.json()["financial_impact"]) == Decimal("24.90")
    assert quantity(sessions) == 19
    assert client.get("/api/workflow/audit-logs").json()[0]["action_type"] == "AUTO_ADJUSTED"


def test_major_is_pending_and_enriched(setup):
    client, sessions, _ = setup
    result = submit(client)
    assert result.status_code == 201
    assert result.json()["status"] == "PENDING_APPROVAL"
    assert quantity(sessions) == 20
    pending = client.get("/api/workflow/pending-approvals").json()[0]
    assert pending["sku"] == "TEST-MILO"
    assert pending["product_name"] == "Milo 1kg"
    assert pending["is_stale"] is False
    assert pending["discrepancy_delta"] == -5
    assert Decimal(pending["financial_impact"]) == Decimal("124.50")
    assert client.get("/api/workflow/audit-logs").json()[0]["action_type"] == "DISCREPANCY_DETECTED"


def test_manager_approval_and_audit(setup):
    client, sessions, _ = setup
    request = submit(client).json()
    result = review(client, request["id"])
    assert result.status_code == 200
    assert result.json()["status"] == "APPROVED"
    assert result.json()["reviewed_by"] == "Store manager"
    assert result.json()["reviewed_at"]
    assert result.json()["review_notes"] == "Verified"
    assert quantity(sessions) == 15
    assert client.get("/api/workflow/pending-approvals").json() == []
    logs = client.get("/api/workflow/audit-logs", params={"action_type": "APPROVAL_GRANTED"}).json()
    assert len(logs) == 1
    assert logs[0]["details"]["before_quantity"] == 20
    assert logs[0]["details"]["after_quantity"] == 15


def test_duplicate_approval_prevention(setup):
    client, sessions, _ = setup
    request_id = submit(client).json()["id"]
    assert review(client, request_id).status_code == 200
    assert review(client, request_id).status_code == 400
    assert review(client, request_id, "REJECT").status_code == 400
    assert quantity(sessions) == 15
    assert len(client.get("/api/workflow/audit-logs").json()) == 2


def test_manager_rejection(setup):
    client, sessions, _ = setup
    request_id = submit(client).json()["id"]
    result = review(client, request_id, "REJECT")
    assert result.status_code == 200
    assert result.json()["status"] == "REJECTED"
    assert quantity(sessions) == 20
    assert review(client, request_id).status_code == 400
    assert client.get("/api/workflow/audit-logs").json()[-1]["action_type"] == "APPROVAL_REJECTED"


@pytest.mark.parametrize("price,count,expected", [
    ("24.99", 18, "AUTO_APPROVED"),  # RM49.98
    ("25.00", 18, "PENDING_APPROVAL"),  # exactly RM50
    ("50.00", 19, "PENDING_APPROVAL"),  # one expensive unit
    ("1.00", 17, "PENDING_APPROVAL"),  # cheap but >2 units
    ("24.90", 22, "AUTO_APPROVED"),  # positive discrepancy
    ("24.90", 20, "AUTO_APPROVED"),  # unchanged count
])
def test_deterministic_boundaries(setup, price, count, expected):
    client, sessions, _ = setup
    with sessions.begin() as db:
        db.get(Product, 1).unit_price = Decimal(price)
    result = submit(client, count)
    assert result.status_code == 201
    assert result.json()["status"] == expected
    assert quantity(sessions) == (count if expected == "AUTO_APPROVED" else 20)


def test_negative_stock_flagged_but_not_approvable(setup):
    client, sessions, _ = setup
    with sessions.begin() as db:
        db.get(Product, 1).system_quantity = 0
    result = submit(client, -1).json()
    assert result["status"] == "PENDING_APPROVAL"
    assert review(client, result["id"]).status_code == 400
    assert quantity(sessions) == 0
    assert review(client, result["id"], "REJECT").status_code == 200


def test_stale_count_cannot_overwrite_new_stock(setup):
    client, sessions, _ = setup
    request_id = submit(client).json()["id"]
    assert submit(client, 19).json()["status"] == "AUTO_APPROVED"
    assert client.get("/api/workflow/pending-approvals").json()[0]["is_stale"] is True
    assert review(client, request_id).status_code == 409
    assert quantity(sessions) == 19
    assert review(client, request_id, "REJECT").status_code == 200


def test_audit_filters_and_pagination(setup):
    client, _, _ = setup
    submit(client)
    submit(client, 19)
    all_logs = client.get("/api/workflow/audit-logs").json()
    assert [x["id"] for x in all_logs] == sorted(x["id"] for x in all_logs)
    assert len(client.get("/api/workflow/audit-logs?product_id=1").json()) == 2
    assert client.get("/api/workflow/audit-logs?product_id=99").json() == []
    assert len(client.get("/api/workflow/audit-logs?offset=1&limit=1").json()) == 1
    assert client.get("/api/workflow/audit-logs?action_type=INVALID").status_code == 422


def test_orbyte_payload_and_log(setup):
    client, sessions, _ = setup
    submit(client, 19)
    request_id = submit(client, 14).json()["id"]
    review(client, request_id)
    rejected_id = submit(client, 9).json()["id"]
    review(client, rejected_id, "REJECT")
    with sessions.begin() as db:
        db.add(Product(id=2, sku="TEST-SARDINES", name="Sardines", system_quantity=3,
                       unit_price=Decimal("9.50"), low_stock_threshold=5))
    result = client.post("/api/integration/orbyte-sync")
    assert result.status_code == 200
    data = result.json()
    assert data["status"] == "SIMULATED_SUCCESS"
    assert data["simulated"] is True
    assert data["payload"]["currency"] == "MYR"
    changes = data["payload"]["inventory_changes"]
    assert len(changes) == 2
    assert [(c["before_quantity"], c["after_quantity"]) for c in changes] == [(20, 19), (19, 14)]
    assert data["payload"]["low_stock_alerts"][0]["sku"] == "TEST-SARDINES"
    logs = client.get("/api/workflow/audit-logs?action_type=ORBYTE_SYNC").json()
    assert logs[0]["details"]["payload"]["inventory_changes"] == changes
    assert client.post("/api/integration/orbyte-sync", json={"since": "2099-01-01T00:00:00Z"}).json()["payload"]["inventory_changes"] == []


def test_input_validation_and_not_found(setup):
    client, _, _ = setup
    body = {"product_id": 1, "physical_counted_qty": 19, "submitted_by": "Clerk", "reason": "Count"}
    for field, value in [("physical_counted_qty", 1.5), ("physical_counted_qty", True),
                         ("submitted_by", "  "), ("reason", "")]:
        assert client.post("/api/workflow/stock-count", json={**body, field: value}).status_code == 422
    assert client.post("/api/workflow/stock-count", json={**body, "product_id": 999}).status_code == 404
    assert review(client, 999).status_code == 404
    assert client.post("/api/workflow/approvals/1/review", json={
        "action": "DELETE", "manager_name": "Manager",
    }).status_code == 422


def test_auto_approved_cannot_be_reviewed(setup):
    client, _, _ = setup
    assert review(client, submit(client, 19).json()["id"]).status_code == 400


def test_price_snapshot_is_immutable(setup):
    client, sessions, _ = setup
    submit(client)
    with sessions.begin() as db:
        db.get(Product, 1).unit_price = Decimal("30.00")
    pending = client.get("/api/workflow/pending-approvals").json()[0]
    assert Decimal(pending["financial_impact"]) == Decimal("124.50")


def test_concurrent_reviews_only_one_succeeds(setup):
    client, sessions, _ = setup
    request_id = submit(client).json()["id"]
    barrier = Barrier(2)
    def worker():
        from fastapi import HTTPException
        barrier.wait()
        with sessions() as db:
            try:
                review_request(db, request_id, ReviewInput(action="APPROVE", manager_name="Manager"))
                return 200
            except HTTPException as error:
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: worker(), range(2)))
    assert sorted(statuses) == [200, 400]
    assert quantity(sessions) == 15
    assert len(client.get("/api/workflow/audit-logs?action_type=APPROVAL_GRANTED").json()) == 1


def test_failed_audit_rolls_back_approval(setup):
    client, sessions, _ = setup
    request_id = submit(client).json()["id"]
    def fail_audit(session, flush_context, instances):
        if any(isinstance(x, AuditLog) for x in session.new):
            raise RuntimeError("Simulated audit persistence failure")
    with sessions() as db:
        event.listen(db, "before_flush", fail_audit)
        with pytest.raises(RuntimeError, match="audit persistence"):
            review_request(db, request_id, ReviewInput(action="APPROVE", manager_name="Manager"))
    assert quantity(sessions) == 20
    with sessions() as db:
        assert db.get(StockAdjustmentRequest, request_id).status.value == "PENDING_APPROVAL"
        assert len(db.scalars(select(AuditLog)).all()) == 1


def test_swagger_openapi_and_products(setup):
    client, _, _ = setup
    assert client.get("/docs").status_code == 200
    assert client.get("/api/products").json()[0]["sku"] == "TEST-MILO"
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/workflow/stock-count" in paths
    assert "/api/integration/orbyte-sync" in paths
