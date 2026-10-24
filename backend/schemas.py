from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import ActionType, AdjustmentStatus, MovementType


class InputModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class StockCountInput(InputModel):
    product_id: int = Field(gt=0)
    physical_counted_qty: int = Field(strict=True, ge=-2_000_000_000, le=2_000_000_000)
    submitted_by: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=2000)


class ReviewInput(InputModel):
    action: Literal["APPROVE", "REJECT"]
    manager_name: str = Field(min_length=1, max_length=120)
    notes: str = Field(default="", max_length=2000)


class AdjustmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    submitted_by: str
    recorded_system_qty: int
    physical_counted_qty: int
    discrepancy_delta: int
    unit_price_snapshot: Decimal
    financial_impact: Decimal
    reason: str
    status: AdjustmentStatus
    reviewed_by: str | None
    review_notes: str | None
    created_at: datetime
    reviewed_at: datetime | None


class PendingApprovalOut(AdjustmentOut):
    product_name: str
    sku: str
    current_system_quantity: int
    is_stale: bool


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    timestamp: datetime
    actor: str
    action_type: ActionType
    product_id: int | None
    details: dict[str, Any]


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sku: str
    name: str
    system_quantity: int
    unit_price: Decimal
    low_stock_threshold: int


class ProductCreate(InputModel):
    sku: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    system_quantity: int = Field(default=0, strict=True, ge=0, le=2_000_000_000)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    low_stock_threshold: int = Field(default=5, strict=True, ge=0, le=2_000_000_000)

    @field_validator("unit_price")
    @classmethod
    def money_precision(cls, value):
        return value.quantize(Decimal("0.01"))


class ProductUpdate(InputModel):
    # Quantities change only through stock movements or the count/approval workflow.
    sku: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    low_stock_threshold: int | None = Field(default=None, strict=True, ge=0, le=2_000_000_000)

    @field_validator("unit_price")
    @classmethod
    def money_precision(cls, value):
        return value.quantize(Decimal("0.01")) if value is not None else None


class StockMovementInput(InputModel):
    product_id: int = Field(gt=0)
    movement_type: Literal["IN", "OUT"]
    quantity: int = Field(strict=True, gt=0, le=2_000_000_000)
    actor: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=2000)


class StockMovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    movement_type: MovementType
    delta: int
    before_quantity: int
    after_quantity: int
    actor: str
    reason: str
    adjustment_request_id: int | None
    created_at: datetime


class ImportRowError(BaseModel):
    row: int
    message: str


class ImportReport(BaseModel):
    dry_run: bool
    valid: bool
    total_rows: int
    created_count: int = 0
    preview: list[ProductCreate] = Field(default_factory=list)
    products: list[ProductOut] = Field(default_factory=list)
    errors: list[ImportRowError] = Field(default_factory=list)


class SyncInput(InputModel):
    actor: str = Field(default="orbyte-demo", min_length=1, max_length=120)
    since: datetime | None = None


class InventoryChange(BaseModel):
    audit_log_id: int
    request_id: int | None
    timestamp: datetime
    product_id: int
    sku: str
    product_name: str
    before_quantity: int
    after_quantity: int
    delta: int
    financial_impact: str


class LowStockAlert(BaseModel):
    product_id: int
    sku: str
    product_name: str
    system_quantity: int
    low_stock_threshold: int


class SyncPayload(BaseModel):
    source: Literal["sme-inventory"]
    destination: Literal["orbyte"]
    currency: Literal["MYR"]
    generated_at: datetime
    since: datetime
    inventory_changes: list[InventoryChange]
    low_stock_alerts: list[LowStockAlert]


class SyncOut(BaseModel):
    status: Literal["SIMULATED_SUCCESS"]
    simulated: Literal[True]
    message: str
    sync_log_id: int
    payload: SyncPayload
