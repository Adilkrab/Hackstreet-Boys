"""Idempotent demo: from the repository root, python -m src.backend.seed_demo."""
import csv
from pathlib import Path
from decimal import Decimal

from sqlalchemy import select

from src.backend.core import Product
from src.backend.database import engine, SessionLocal
from src.backend.schemas import ReviewInput, StockCountInput
from src.backend.services.automation import review_request, submit_stock_count
from src.backend.models import StockAdjustmentRequest
from src.backend.schema_setup import prepare_database

with (Path(__file__).resolve().parents[1] / "sample_data" / "products.csv").open(
    encoding="utf-8", newline=""
) as csv_file:
    PRODUCTS = [
        (row["sku"], row["name"], int(row["system_quantity"]),
         row["unit_price"], int(row["low_stock_threshold"]))
        for row in csv.DictReader(csv_file)
    ]


def seed_demo():
    prepare_database(engine)
    with SessionLocal.begin() as db:
        for sku, name, quantity, price, threshold in PRODUCTS:
            if not db.scalar(select(Product).where(Product.sku == sku)):
                db.add(Product(sku=sku, name=name, system_quantity=quantity,
                               unit_price=Decimal(price), low_stock_threshold=threshold))
    scenarios = [
        ("MY-MAGGI-KARI", -1, "Minor shelf count correction", None),
        ("MY-MILO-1KG", -5, "Damaged cartons verified by manager", "APPROVE"),
        ("MY-OIL-5KG", -4, "Initial count missed backroom stock", "REJECT"),
    ]
    for sku, delta, label, decision in scenarios:
        reason = f"DEMO: {label}"
        with SessionLocal() as db:
            existing = db.scalar(select(StockAdjustmentRequest).where(StockAdjustmentRequest.reason == reason))
            product = db.scalar(select(Product).where(Product.sku == sku))
            product_id, quantity = product.id, product.system_quantity
            existing_id = existing.id if existing else None
            existing_status = existing.status.value if existing else None
        if existing_id:
            print(f"Already seeded: {label} (#{existing_id}, {existing_status})")
            continue
        with SessionLocal() as db:
            request = submit_stock_count(db, StockCountInput(
                product_id=product_id, physical_counted_qty=quantity + delta,
                submitted_by="Demo stock clerk", reason=reason,
            ))
            request_id, status = request.id, request.status.value
        if decision:
            with SessionLocal() as db:
                request = review_request(db, request_id, ReviewInput(
                    action=decision, manager_name="Demo store manager", notes=label,
                ))
                status = request.status.value
        print(f"{label}: request #{request_id} -> {status}")
    print("Five products ready. Open /docs; use GET /api/products to find product IDs.")


if __name__ == "__main__":
    seed_demo()
