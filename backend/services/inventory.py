"""Read-only product lookup for the demo; core CRUD belongs to Member 1."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..core import Product


def list_products(db: Session):
    return db.scalars(select(Product).order_by(Product.id)).all()
