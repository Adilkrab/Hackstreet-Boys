"""Replace the standalone core by setting WORKFLOW_CORE_MODULE=your_app.models."""
import importlib
import os
from decimal import Decimal

from sqlalchemy import CheckConstraint, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

core_module = os.getenv("WORKFLOW_CORE_MODULE")
if core_module:
    core = importlib.import_module(core_module)
    Base, Product = core.Base, core.Product
else:
    class Base(DeclarativeBase):
        pass

    class Product(Base):
        __tablename__ = "products"
        __table_args__ = (
            CheckConstraint("system_quantity >= 0"),
            CheckConstraint("unit_price >= 0"),
            CheckConstraint("low_stock_threshold >= 0"),
        )

        id: Mapped[int] = mapped_column(primary_key=True)
        sku: Mapped[str] = mapped_column(String(80), unique=True, index=True)
        name: Mapped[str] = mapped_column(String(200))
        system_quantity: Mapped[int] = mapped_column(Integer)
        unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
        low_stock_threshold: Mapped[int] = mapped_column(Integer, default=5)
