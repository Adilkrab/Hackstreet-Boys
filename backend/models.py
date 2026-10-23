from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import JSON, CheckConstraint, DateTime, Enum as SAEnum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .core import Base, Product


def utcnow():
    return datetime.now(timezone.utc)


class AdjustmentStatus(str, Enum):
    AUTO_APPROVED = "AUTO_APPROVED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ActionType(str, Enum):
    PRODUCT_CREATED = "PRODUCT_CREATED"
    PRODUCT_UPDATED = "PRODUCT_UPDATED"
    STOCK_IN = "STOCK_IN"
    STOCK_OUT = "STOCK_OUT"
    INVENTORY_IMPORTED = "INVENTORY_IMPORTED"
    DISCREPANCY_DETECTED = "DISCREPANCY_DETECTED"
    AUTO_ADJUSTED = "AUTO_ADJUSTED"
    APPROVAL_GRANTED = "APPROVAL_GRANTED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
    ORBYTE_SYNC = "ORBYTE_SYNC"


class StockAdjustmentRequest(Base):
    __tablename__ = "stock_adjustment_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey(Product.id), index=True)
    submitted_by: Mapped[str] = mapped_column(String(120))
    recorded_system_qty: Mapped[int]
    physical_counted_qty: Mapped[int]
    discrepancy_delta: Mapped[int]
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    financial_impact: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[AdjustmentStatus] = mapped_column(
        SAEnum(AdjustmentStatus, native_enum=False, create_constraint=True), index=True
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    actor: Mapped[str] = mapped_column(String(120))
    action_type: Mapped[ActionType] = mapped_column(
        SAEnum(ActionType, native_enum=False, create_constraint=True), index=True
    )
    product_id: Mapped[int | None] = mapped_column(ForeignKey(Product.id), nullable=True, index=True)
    details: Mapped[dict] = mapped_column(JSON)


class MovementType(str, Enum):
    OPENING = "OPENING"
    IN = "IN"
    OUT = "OUT"
    ADJUSTMENT = "ADJUSTMENT"


class StockMovement(Base):
    __tablename__ = "stock_movements"
    __table_args__ = (
        CheckConstraint("before_quantity >= 0 AND after_quantity >= 0"),
        CheckConstraint("after_quantity - before_quantity = delta"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey(Product.id), index=True)
    movement_type: Mapped[MovementType] = mapped_column(
        SAEnum(MovementType, native_enum=False, create_constraint=True)
    )
    delta: Mapped[int]
    before_quantity: Mapped[int]
    after_quantity: Mapped[int]
    actor: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str] = mapped_column(Text)
    adjustment_request_id: Mapped[int | None] = mapped_column(
        ForeignKey(StockAdjustmentRequest.id), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
