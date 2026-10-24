"""Product, movement and import checks on isolated databases."""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from threading import Barrier

import pytest
from fastapi import HTTPException
from openpyxl import Workbook
from sqlalchemy import event, select

from src.backend.core import Product
from src.backend.models import AuditLog, StockMovement
from src.backend.schemas import StockMovementInput
from src.backend.services.inventory import record_stock_movement
from tests.test_workflow import setup  # Reuse Member 3's isolated SQLite fixture.

HEADER = "sku,name,system_quantity,unit_price,low_stock_threshold\n"
PRODUCT = {"sku": "NEW-RICE", "name": "Rice", "system_quantity": 10,
           "unit_price": "25.50", "low_stock_threshold": 3}


def create(client, **changes):
    return client.post("/api/products?actor=Clerk", json={**PRODUCT, **changes})


def move(client, kind="IN", amount=5):
    return client.post("/api/stock-movements", json={
        "product_id": 1, "movement_type": kind, "quantity": amount,
        "actor": "Clerk", "reason": "Delivery" if kind == "IN" else "Sale",
    })


def upload(client, content, *, dry_run=True, filename="inventory.csv"):
    return client.post("/api/inventory/import", files={"file": (filename, content)},
                       data={"dry_run": str(dry_run).lower(), "actor": "Importer"})


def test_product_create_update_and_opening_history(setup):
    client, _, _ = setup
    result = create(client)
    assert result.status_code == 201
    product = result.json()
    assert product["system_quantity"] == 10
    assert product["unit_price"] == "25.50"
    history = client.get(f"/api/stock-movements?product_id={product['id']}").json()
    assert [(h["movement_type"], h["delta"]) for h in history] == [("OPENING", 10)]
    result = client.patch(f"/api/products/{product['id']}?actor=Manager", json={"name": "Jasmine Rice", "unit_price": "26.00"})
    assert result.status_code == 200
    assert client.get(f"/api/products/{product['id']}").json()["name"] == "Jasmine Rice"
    assert client.get("/api/products?offset=1&limit=1").json()[0]["id"] == product["id"]


def test_duplicate_sku_and_invalid_edits_do_not_change_product(setup):
    client, _, _ = setup
    assert create(client, sku="TEST-MILO").status_code == 409
    for data in ({"system_quantity": 999}, {"name": None}, {}, {"unit_price": "NaN"}):
        assert client.patch("/api/products/1", json=data).status_code == 422
    assert client.get("/api/products/1").json()["system_quantity"] == 20
    assert client.patch("/api/products/999", json={"name": "New"}).status_code == 404
    assert client.get("/api/products/999").status_code == 404


@pytest.mark.parametrize("changes", [
    {"system_quantity": -1}, {"system_quantity": True}, {"unit_price": "1.001"},
    {"unit_price": "Infinity"}, {"unit_price": "-0.01"}, {"name": "  "},
    {"low_stock_threshold": -1}, {"unit_price": "10000000000.00"},
])
def test_invalid_products(setup, changes):
    assert create(setup[0], **changes).status_code == 422


def test_stock_in_out_history_and_low_stock(setup):
    client, _, _ = setup
    assert move(client, "IN", 5).json()["after_quantity"] == 25
    assert move(client, "OUT", 20).json()["after_quantity"] == 5
    assert client.get("/api/alerts").json()[0]["product_id"] == 1
    history = client.get("/api/stock-movements?product_id=1").json()
    assert [h["delta"] for h in history] == [5, -20]
    changes = client.post("/api/integration/orbyte-sync").json()["payload"]["inventory_changes"]
    assert [change["delta"] for change in changes] == [5, -20]
    assert all(change["request_id"] is None for change in changes)


def test_insufficient_stock_and_invalid_movements_are_atomic(setup):
    client, _, _ = setup
    assert move(client, "OUT", 21).status_code == 409
    assert move(client, "IN", 2_000_000_000).status_code == 409
    for amount in (0, -1, 1.5, True):
        assert move(client, "IN", amount).status_code == 422
    assert client.get("/api/products/1").json()["system_quantity"] == 20
    assert client.get("/api/stock-movements").json() == []
    assert client.get("/api/workflow/audit-logs").json() == []


def test_stock_change_marks_pending_count_stale(setup):
    client, _, _ = setup
    request = client.post("/api/workflow/stock-count", json={
        "product_id": 1, "physical_counted_qty": 10, "submitted_by": "Clerk", "reason": "Count",
    }).json()
    move(client)
    assert client.get("/api/workflow/pending-approvals").json()[0]["is_stale"] is True
    assert client.post(f"/api/workflow/approvals/{request['id']}/review", json={
        "action": "APPROVE", "manager_name": "Manager",
    }).status_code == 409


def test_stock_round_trip_still_invalidates_old_count(setup):
    client, _, _ = setup
    request = client.post("/api/workflow/stock-count", json={
        "product_id": 1, "physical_counted_qty": 10, "submitted_by": "Clerk", "reason": "Count",
    }).json()
    assert move(client, "OUT", 5).status_code == 201
    assert move(client, "IN", 5).status_code == 201
    # Stock is back to 20, but this count predates both intervening movements.
    assert client.get("/api/workflow/pending-approvals").json()[0]["is_stale"] is True
    assert client.post(f"/api/workflow/approvals/{request['id']}/review", json={
        "action": "APPROVE", "manager_name": "Manager",
    }).status_code == 409
    assert client.get("/api/products/1").json()["system_quantity"] == 20


def test_movements_before_count_and_noop_counts_do_not_make_it_stale(setup):
    client, _, _ = setup
    move(client, "OUT", 5)
    request = client.post("/api/workflow/stock-count", json={
        "product_id": 1, "physical_counted_qty": 5, "submitted_by": "Clerk", "reason": "Count",
    }).json()
    client.post("/api/workflow/stock-count", json={
        "product_id": 1, "physical_counted_qty": 15, "submitted_by": "Clerk", "reason": "Unchanged count",
    })
    assert client.get("/api/workflow/pending-approvals").json()[0]["is_stale"] is False
    assert client.post(f"/api/workflow/approvals/{request['id']}/review", json={
        "action": "APPROVE", "manager_name": "Manager",
    }).status_code == 200


def test_pending_counts_track_their_own_submission_boundary(setup):
    client, _, _ = setup
    for count in (10, 5):
        client.post("/api/workflow/stock-count", json={
            "product_id": 1, "physical_counted_qty": count, "submitted_by": "Clerk", "reason": "Count",
        })
        if count == 10:
            move(client, "OUT", 5)
    pending = client.get("/api/workflow/pending-approvals").json()
    assert [item["is_stale"] for item in pending] == [True, False]


def test_other_product_movements_do_not_invalidate_pending_count(setup):
    client, _, _ = setup
    request = client.post("/api/workflow/stock-count", json={
        "product_id": 1, "physical_counted_qty": 10, "submitted_by": "Clerk", "reason": "Count",
    }).json()
    other = create(client).json()
    client.post("/api/stock-movements", json={
        "product_id": other["id"], "movement_type": "OUT", "quantity": 2, "actor": "Clerk", "reason": "Sale",
    })
    assert client.get("/api/workflow/pending-approvals").json()[0]["is_stale"] is False
    assert client.post(f"/api/workflow/approvals/{request['id']}/review", json={
        "action": "APPROVE", "manager_name": "Manager",
    }).status_code == 200


def test_workflow_records_movements_only_when_stock_changes(setup):
    client, _, _ = setup
    def count(quantity):
        return client.post("/api/workflow/stock-count", json={
            "product_id": 1, "physical_counted_qty": quantity, "submitted_by": "Clerk", "reason": "Count",
        }).json()
    count(19)
    pending = count(10)
    assert len(client.get("/api/stock-movements").json()) == 1
    assert client.post(f"/api/workflow/approvals/{pending['id']}/review", json={
        "action": "APPROVE", "manager_name": "Manager",
    }).status_code == 200
    history = client.get("/api/stock-movements").json()
    assert [h["delta"] for h in history] == [-1, -9]
    assert all(h["movement_type"] == "ADJUSTMENT" for h in history)
    assert history[-1]["adjustment_request_id"] == pending["id"]


def test_csv_preview_commit_and_duplicate_reimport(setup):
    client, _, _ = setup
    content = (HEADER + "IMPORT-A,Tea,8,4.50,2\nIMPORT-B,Coffee,0,12.00,3\n").encode()
    preview = upload(client, content).json()
    assert preview["valid"] is True
    assert preview["created_count"] == 0
    assert preview["preview"][0]["sku"] == "IMPORT-A"
    assert len(client.get("/api/products").json()) == 1
    result = upload(client, content, dry_run=False)
    assert result.status_code == 200
    assert result.json()["created_count"] == 2
    assert result.json()["products"][0]["system_quantity"] == 8
    assert upload(client, content, dry_run=False).status_code == 422
    assert len(client.get("/api/products").json()) == 3
    history = client.get("/api/stock-movements").json()
    assert len(history) == 1  # No movement for zero opening stock.


@pytest.mark.parametrize("rows", [
    "GOOD,Tea,8,4.50,2\nBAD,Coffee,-1,12.00,3\n",
    "SAME,Tea,8,4.50,2\nSAME,Coffee,2,12.00,3\n",
    "TEST-MILO,Tea,8,4.50,2\nNEW,Coffee,2,12.00,3\n",
    "BAD,Tea,1.5,4.50,2\n",
    "BAD,Tea,2,NaN,2\n",
    "BAD,=SUM(A1),2,4.50,2\n",
])
def test_invalid_import_saves_nothing_and_reports_row(setup, rows):
    client, _, _ = setup
    content = (HEADER + rows).encode()
    preview = upload(client, content).json()
    assert preview["valid"] is False
    assert preview["errors"][0]["row"] >= 2
    assert upload(client, content, dry_run=False).status_code == 422
    assert len(client.get("/api/products").json()) == 1
    assert client.get("/api/stock-movements").json() == []
    assert client.get("/api/workflow/audit-logs").json() == []


def test_xlsx_import_and_formula_rejection(setup):
    client, _, _ = setup
    book = Workbook()
    book.active.append(HEADER.strip().split(","))
    book.active.append(["XLSX-TEA", "Tea", 8, 4.50, 2])
    output = BytesIO()
    book.save(output)
    result = upload(client, output.getvalue(), dry_run=False, filename="inventory.xlsx")
    assert result.status_code == 200
    assert result.json()["products"][0]["unit_price"] == "4.50"
    book.active["A2"] = "XLSX-OTHER"
    book.active["C2"] = "=1+2"
    output = BytesIO()
    book.save(output)
    assert upload(client, output.getvalue(), filename="inventory.xlsx").json()["valid"] is False
    book.close()


@pytest.mark.parametrize("content,filename,status", [
    (b"", "inventory.csv", 422), (b"sku,name\nA,Tea", "inventory.csv", 422),
    (b"invalid", "inventory.xlsx", 422), (b"invalid", "inventory.xls", 415),
    (b"\xff", "inventory.csv", 422), (b"a" * (5 * 1024 * 1024 + 1), "inventory.csv", 413),
], ids=["empty", "headers", "corrupt-xlsx", "legacy-xls", "encoding", "oversized"])
def test_unreadable_imports(setup, content, filename, status):
    assert upload(setup[0], content, filename=filename).status_code == status


def test_concurrent_stock_out_cannot_oversell(setup):
    _, sessions, _ = setup
    barrier = Barrier(2)
    def worker(_):
        barrier.wait()
        with sessions() as db:
            try:
                record_stock_movement(db, StockMovementInput(
                    product_id=1, movement_type="OUT", quantity=15, actor="Clerk", reason="Sale",
                ))
                return 201
            except HTTPException as error:
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(worker, range(2))) == [201, 409]
    with sessions() as db:
        assert db.get(Product, 1).system_quantity == 5
        assert len(db.scalars(select(StockMovement)).all()) == 1


def test_import_database_failure_rolls_back_whole_batch(setup):
    _, sessions, _ = setup
    from src.backend.services.import_service import import_inventory
    with sessions() as db:
        def fail_import(session, *_):
            if any(isinstance(item, AuditLog) and item.action_type.value == "INVENTORY_IMPORTED" for item in session.new):
                raise RuntimeError("Simulated failure")
        event.listen(db, "before_flush", fail_import)
        with pytest.raises(RuntimeError, match="Simulated failure"):
            import_inventory(db, "inventory.csv", (HEADER + "NEW-A,Tea,3,4.50,2\nNEW-B,Coffee,2,8.00,1\n").encode(), "Importer", False)
    with sessions() as db:
        assert len(db.scalars(select(Product)).all()) == 1
        assert db.scalars(select(StockMovement)).all() == []
        assert db.scalars(select(AuditLog)).all() == []
