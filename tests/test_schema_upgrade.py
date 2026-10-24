from decimal import Decimal
import os
from pathlib import Path
import subprocess
import sys

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from src.backend.core import Base, Product
from src.backend.models import ActionType, AuditLog
from src.backend.schema_setup import prepare_database


def test_original_sqlite_audit_upgrade_preserves_data_and_is_idempotent(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.sqlite3'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add(Product(id=1, sku="OLD", name="Existing stock", system_quantity=12,
                            unit_price=Decimal("3.00"), low_stock_threshold=2))
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE audit_logs")
        connection.exec_driver_sql("""CREATE TABLE audit_logs (
            id INTEGER NOT NULL PRIMARY KEY,
            timestamp DATETIME NOT NULL,
            actor VARCHAR(120) NOT NULL,
            action_type VARCHAR(20) NOT NULL CHECK (action_type IN (
                'DISCREPANCY_DETECTED', 'AUTO_ADJUSTED', 'APPROVAL_GRANTED', 'APPROVAL_REJECTED', 'ORBYTE_SYNC')),
            product_id INTEGER REFERENCES products(id),
            details JSON NOT NULL
        )""")
        connection.exec_driver_sql("""INSERT INTO audit_logs VALUES (
            7, '2026-10-22 00:00:00', 'Clerk', 'AUTO_ADJUSTED', 1, '{}'
        )""")
        connection.exec_driver_sql("DROP TABLE stock_movements")
    prepare_database(engine)
    prepare_database(engine)
    with Session(engine) as session, session.begin():
        assert session.get(Product, 1).system_quantity == 12
        assert session.get(AuditLog, 7).actor == "Clerk"
        session.add(AuditLog(actor="Clerk", action_type=ActionType.STOCK_IN, product_id=1, details={}))
    with Session(engine) as session:
        assert len(session.scalars(select(AuditLog)).all()) == 2
    assert inspect(engine).has_table("stock_movements")
    engine.dispose()


def test_seed_command_runs_twice_without_overwriting_stock(tmp_path):
    database = tmp_path / "seed.sqlite3"
    environment = {**os.environ, "WORKFLOW_DATABASE_URL": f"sqlite:///{database.as_posix()}",
                   "PYTHONIOENCODING": "cp1252"}
    for _ in range(2):
        result = subprocess.run([sys.executable, "-m", "src.backend.seed_demo"],
                                cwd=Path(__file__).resolve().parents[1], env=environment,
                                capture_output=True, timeout=30)
        assert result.returncode == 0, result.stderr.decode("cp1252")
    engine = create_engine(f"sqlite:///{database.as_posix()}")
    with Session(engine) as session:
        assert len(session.scalars(select(Product)).all()) == 5
        assert len(session.scalars(select(AuditLog)).all()) == 5
        assert session.scalar(select(Product).where(Product.sku == "MY-MILO-1KG")).system_quantity == 35
    engine.dispose()
