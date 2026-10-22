from datetime import timedelta, timezone

from sqlalchemy import select

from ..core import Product
from ..schemas import SyncInput, SyncOut, SyncPayload
from ..models import ActionType, AuditLog, utcnow
from .automation import audit, transaction


def simulate_orbyte_sync(db, data: SyncInput):
    now = utcnow()
    since = data.since or now - timedelta(hours=24)
    if since.tzinfo is None:
        since = since.replace(tzinfo=timezone.utc)
    with transaction(db):
        changes = db.execute(
            select(AuditLog, Product).join(Product, Product.id == AuditLog.product_id)
            .where(AuditLog.timestamp >= since, AuditLog.timestamp <= now,
                   AuditLog.action_type.in_([ActionType.AUTO_ADJUSTED, ActionType.APPROVAL_GRANTED]))
            .order_by(AuditLog.timestamp, AuditLog.id)
        ).all()
        low_stock = db.scalars(
            select(Product).where(Product.system_quantity <= Product.low_stock_threshold).order_by(Product.id)
        ).all()
        payload = SyncPayload(
            source="sme-inventory", destination="orbyte", currency="MYR", generated_at=now, since=since,
            inventory_changes=[
                {
                    "audit_log_id": log.id, "request_id": log.details["request_id"],
                    "timestamp": log.timestamp, "product_id": product.id,
                    "sku": product.sku, "product_name": product.name,
                    "before_quantity": log.details["before_quantity"],
                    "after_quantity": log.details["after_quantity"],
                    "delta": log.details["discrepancy_delta"],
                    "financial_impact": log.details["financial_impact"],
                } for log, product in changes
            ],
            low_stock_alerts=[
                {"product_id": p.id, "sku": p.sku, "product_name": p.name,
                 "system_quantity": p.system_quantity, "low_stock_threshold": p.low_stock_threshold}
                for p in low_stock
            ],
        )
        entry = audit(db, data.actor, ActionType.ORBYTE_SYNC, None, {
            "simulated": True, "inventory_change_count": len(changes),
            "low_stock_alert_count": len(low_stock), "payload": payload.model_dump(mode="json"),
        })
        db.flush()
        log_id = entry.id
    return SyncOut(
        status="SIMULATED_SUCCESS", simulated=True,
        message="Payload generated locally. No data was sent to Orbyte.",
        sync_log_id=log_id, payload=payload,
    )
