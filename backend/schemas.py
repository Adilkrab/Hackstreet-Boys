from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import ActionType, AdjustmentStatus


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


class SyncInput(InputModel):
    actor: str = Field(default="orbyte-demo", min_length=1, max_length=120)
    since: datetime | None = None


class InventoryChange(BaseModel):
    audit_log_id: int
    request_id: int
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
