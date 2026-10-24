from typing import Annotated

from fastapi import APIRouter, File, Form, Query, UploadFile
from sqlalchemy import select

from ..core import Product
from ..models import StockMovement
from ..schemas import (
    ImportReport, LowStockAlert, ProductCreate, ProductOut, ProductUpdate,
    StockMovementInput, StockMovementOut,
)
from ..services import inventory
from ..services.import_service import MAX_BYTES, import_inventory
from .workflow import DB

router = APIRouter(prefix="/api", tags=["Inventory"])
Actor = Annotated[str, Query(min_length=1, max_length=120, pattern=r"\S")]


@router.get("/products", response_model=list[ProductOut])
def products(db: DB, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    return inventory.list_products(db, offset, limit)


@router.get("/products/{product_id}", response_model=ProductOut)
def product(product_id: int, db: DB):
    return inventory.get_product(db, product_id)


@router.post("/products", response_model=ProductOut, status_code=201)
def create_product(data: ProductCreate, db: DB, actor: Actor = "Inventory staff"):
    return inventory.create_product(db, data, actor.strip())


@router.patch("/products/{product_id}", response_model=ProductOut)
def edit_product(product_id: int, data: ProductUpdate, db: DB, actor: Actor = "Inventory staff"):
    return inventory.edit_product(db, product_id, data, actor.strip())


@router.post("/stock-movements", response_model=StockMovementOut, status_code=201)
def stock_movement(data: StockMovementInput, db: DB):
    return inventory.record_stock_movement(db, data)


@router.get("/stock-movements", response_model=list[StockMovementOut])
def movements(db: DB, product_id: int | None = Query(None, gt=0),
              offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    query = select(StockMovement)
    if product_id is not None:
        query = query.where(StockMovement.product_id == product_id)
    return db.scalars(query.order_by(StockMovement.created_at, StockMovement.id).offset(offset).limit(limit)).all()


@router.get("/alerts", response_model=list[LowStockAlert])
def alerts(db: DB, offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500)):
    products = db.scalars(select(Product).where(Product.system_quantity <= Product.low_stock_threshold)
                          .order_by(Product.id).offset(offset).limit(limit)).all()
    return [LowStockAlert(product_id=p.id, sku=p.sku, product_name=p.name,
                          system_quantity=p.system_quantity, low_stock_threshold=p.low_stock_threshold) for p in products]


@router.post("/inventory/import", response_model=ImportReport)
def upload_inventory(db: DB, file: Annotated[UploadFile, File()],
                     actor: Annotated[str, Form(min_length=1, max_length=120, pattern=r"\S")] = "Inventory staff",
                     dry_run: Annotated[bool, Form()] = True):
    """Preview by default. Set dry_run=false to create all rows or none."""
    try:
        content = file.file.read(MAX_BYTES + 1)
        return import_inventory(db, file.filename, content, actor.strip(), dry_run)
    finally:
        file.file.close()
