"""Shared product operations and the single stock-changing function."""
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core import Product
from ..models import ActionType, MovementType, StockMovement
from ..schemas import ProductCreate, ProductUpdate, StockMovementInput
from .common import audit, transaction


def list_products(db: Session, offset=0, limit=100):
    return db.scalars(select(Product).order_by(Product.id).offset(offset).limit(limit)).all()


def get_product(db: Session, product_id: int, *, lock=False):
    query = select(Product).where(Product.id == product_id)
    product = db.scalar(query.with_for_update() if lock else query)
    if product is None:
        raise HTTPException(404, "Product not found.")
    return product


def apply_stock_change(db, product, new_quantity, movement_type, actor, reason, request_id=None):
    """Caller owns the transaction and row lock. Keep quantity and history together."""
    if not 0 <= new_quantity <= 2_000_000_000:
        raise HTTPException(409, "Resulting stock must be between 0 and 2000000000.")
    before = product.system_quantity
    if new_quantity == before:
        return None
    result = db.execute(update(Product).where(
        Product.id == product.id, Product.system_quantity == before,
    ).values(system_quantity=new_quantity))
    if result.rowcount != 1:
        raise HTTPException(409, "Stock changed during this operation. Refresh and try again.")
    movement = StockMovement(
        product_id=product.id, movement_type=movement_type, delta=new_quantity - before,
        before_quantity=before, after_quantity=new_quantity, actor=actor, reason=reason,
        adjustment_request_id=request_id,
    )
    db.add(movement)
    return movement


def add_product(db, data: ProductCreate, actor: str):
    """Create inside an existing transaction; imports use the same opening history."""
    values = data.model_dump()
    opening = values.pop("system_quantity")
    product = Product(**values, system_quantity=0)
    db.add(product)
    db.flush()
    apply_stock_change(db, product, opening, MovementType.OPENING, actor, "Opening stock")
    audit(db, actor, ActionType.PRODUCT_CREATED, product.id,
          {"sku": product.sku, "opening_quantity": opening})
    return product


def create_product(db, data: ProductCreate, actor: str):
    try:
        with transaction(db):
            product = add_product(db, data, actor)
        return product
    except IntegrityError as error:
        raise HTTPException(409, "SKU already exists or product violates database constraints.") from error


def edit_product(db, product_id: int, data: ProductUpdate, actor: str):
    changes = data.model_dump(exclude_unset=True)
    if not changes or any(value is None for value in changes.values()):
        raise HTTPException(422, "Provide at least one non-null product field. Stock quantities cannot be edited here.")
    try:
        with transaction(db):
            product = get_product(db, product_id, lock=True)
            before = {key: str(getattr(product, key)) for key in changes}
            for key, value in changes.items():
                setattr(product, key, value)
            audit(db, actor, ActionType.PRODUCT_UPDATED, product.id,
                  {"before": before, "after": {key: str(value) for key, value in changes.items()}})
        return product
    except IntegrityError as error:
        raise HTTPException(409, "SKU already exists or product violates database constraints.") from error


def record_stock_movement(db, data: StockMovementInput):
    with transaction(db):
        product = get_product(db, data.product_id, lock=True)
        before = product.system_quantity
        delta = data.quantity if data.movement_type == "IN" else -data.quantity
        movement = apply_stock_change(
            db, product, before + delta, MovementType(data.movement_type), data.actor, data.reason,
        )
        db.flush()
        audit(db, data.actor, ActionType.STOCK_IN if delta > 0 else ActionType.STOCK_OUT,
              product.id, {
                  "movement_id": movement.id, "before_quantity": before,
                  "after_quantity": before + delta, "discrepancy_delta": delta,
                  "financial_impact": str(abs(delta) * product.unit_price), "reason": data.reason,
              })
    return movement
