from contextlib import contextmanager
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from ..core import Product
from ..schemas import ReviewInput, StockCountInput
from ..models import ActionType, AdjustmentStatus as Status, AuditLog, StockAdjustmentRequest, utcnow


@contextmanager
def transaction(db: Session):
    """Own one fresh session transaction; serialize SQLite writes before reading."""
    if db.in_transaction():
        raise RuntimeError("Workflow writes require a fresh session (no active transaction).")
    try:
        if db.get_bind().dialect.name == "sqlite":
            db.execute(text("BEGIN IMMEDIATE"))
        else:
            db.begin()
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise


def audit(db, actor, action, product_id, details):
    entry = AuditLog(actor=actor, action_type=action, product_id=product_id, details=details)
    db.add(entry)
    return entry


def details_for(request, before, after, **extra):
    return {
        "request_id": request.id,
        "before_quantity": before,
        "after_quantity": after,
        "physical_counted_qty": request.physical_counted_qty,
        "discrepancy_delta": request.discrepancy_delta,
        "financial_impact": str(request.financial_impact),
        "unit_price_snapshot": str(request.unit_price_snapshot),
        "currency": "MYR",
        **extra,
    }


def submit_stock_count(db: Session, data: StockCountInput):
    with transaction(db):
        product = db.scalar(select(Product).where(Product.id == data.product_id).with_for_update())
        if product is None:
            raise HTTPException(404, "Product not found.")
        before = product.system_quantity
        price = Decimal(str(product.unit_price))
        if price < 0:
            raise HTTPException(409, "Product unit price must not be negative.")
        delta = data.physical_counted_qty - before
        impact = abs(delta) * price
        auto = abs(delta) <= 2 and impact < Decimal("50.00") and data.physical_counted_qty >= 0
        request = StockAdjustmentRequest(
            **data.model_dump(),
            recorded_system_qty=before,
            discrepancy_delta=delta,
            unit_price_snapshot=price,
            financial_impact=impact,
            status=Status.AUTO_APPROVED if auto else Status.PENDING_APPROVAL,
        )
        db.add(request)
        db.flush()
        if auto:
            product.system_quantity = data.physical_counted_qty
        audit(
            db, data.submitted_by,
            ActionType.AUTO_ADJUSTED if auto else ActionType.DISCREPANCY_DETECTED,
            product.id,
            details_for(request, before, product.system_quantity, reason=data.reason,
                        negative_count=data.physical_counted_qty < 0),
        )
    return request


def review_request(db: Session, request_id: int, data: ReviewInput):
    with transaction(db):
        request = db.scalar(
            select(StockAdjustmentRequest).where(StockAdjustmentRequest.id == request_id).with_for_update()
        )
        if request is None:
            raise HTTPException(404, "Stock adjustment request not found.")
        if request.status != Status.PENDING_APPROVAL:
            raise HTTPException(400, "Request has already been processed; duplicate reviews are not allowed.")
        product = db.scalar(select(Product).where(Product.id == request.product_id).with_for_update())
        if product is None:
            raise HTTPException(404, "Product not found.")
        before = product.system_quantity
        approve = data.action == "APPROVE"
        if approve:
            if request.physical_counted_qty < 0:
                raise HTTPException(400, "Cannot approve negative stock. Reject this request and submit a corrected count.")
            if before != request.recorded_system_qty:
                raise HTTPException(409, "Stock changed since this count. Reject this request and submit a fresh count.")
            # Compare-and-set also protects integrations on databases without SQLite's write lock.
            changed = db.execute(
                update(Product).where(
                    Product.id == product.id,
                    Product.system_quantity == request.recorded_system_qty,
                ).values(system_quantity=request.physical_counted_qty)
            )
            if changed.rowcount != 1:
                raise HTTPException(409, "Stock changed during review; submit a fresh count.")
        request.status = Status.APPROVED if approve else Status.REJECTED
        request.reviewed_by = data.manager_name
        request.reviewed_at = utcnow()
        request.review_notes = data.notes
        audit(
            db, data.manager_name,
            ActionType.APPROVAL_GRANTED if approve else ActionType.APPROVAL_REJECTED,
            product.id,
            details_for(request, before, request.physical_counted_qty if approve else before,
                        notes=data.notes),
        )
    return request
