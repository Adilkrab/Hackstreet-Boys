from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core import Product
from ..database import get_db
from ..schemas import AdjustmentOut, AuditLogOut, PendingApprovalOut, ReviewInput, StockCountInput
from ..services.automation import review_request, submit_stock_count
from ..services.inventory import stock_changed_since_count
from ..models import ActionType, AdjustmentStatus, AuditLog, StockAdjustmentRequest

router = APIRouter(prefix="/api/workflow", tags=["Inventory workflow"])
DB = Annotated[Session, Depends(get_db)]


@router.post("/stock-count", response_model=AdjustmentOut, status_code=201)
def stock_count(data: StockCountInput, db: DB):
    """Auto-approve only when |delta| <= 2 AND impact < RM50 AND count >= 0."""
    return submit_stock_count(db, data)


@router.get("/pending-approvals", response_model=list[PendingApprovalOut])
def pending_approvals(db: DB, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    rows = db.execute(
        select(StockAdjustmentRequest, Product, stock_changed_since_count(
            StockAdjustmentRequest.id, StockAdjustmentRequest.product_id
        ))
        .join(Product, Product.id == StockAdjustmentRequest.product_id)
        .where(StockAdjustmentRequest.status == AdjustmentStatus.PENDING_APPROVAL)
        .order_by(StockAdjustmentRequest.created_at, StockAdjustmentRequest.id).offset(offset).limit(limit)
    ).all()
    return [
        PendingApprovalOut(
            **AdjustmentOut.model_validate(request).model_dump(),
            product_name=product.name, sku=product.sku,
            current_system_quantity=product.system_quantity,
            is_stale=product.system_quantity != request.recorded_system_qty or changed_since_count,
        ) for request, product, changed_since_count in rows
    ]


@router.post("/approvals/{request_id}/review", response_model=AdjustmentOut,
             responses={400: {"description": "Already processed or negative stock"},
                        404: {"description": "Request or product not found"},
                        409: {"description": "Stock changed since count"}})
def review(request_id: int, data: ReviewInput, db: DB):
    """Demo manager identity is supplied by the caller; this is not authentication."""
    return review_request(db, request_id, data)


@router.get("/audit-logs", response_model=list[AuditLogOut])
def audit_logs(
    db: DB, product_id: int | None = Query(None, gt=0), action_type: ActionType | None = None,
    offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500),
):
    """Oldest first, then ID; use offset/limit for pagination."""
    query = select(AuditLog)
    if product_id is not None:
        query = query.where(AuditLog.product_id == product_id)
    if action_type is not None:
        query = query.where(AuditLog.action_type == action_type)
    return db.scalars(query.order_by(AuditLog.timestamp, AuditLog.id).offset(offset).limit(limit)).all()
