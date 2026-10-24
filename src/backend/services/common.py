from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models import AuditLog


@contextmanager
def transaction(db: Session):
    """Serialize SQLite writers before reading; commit stock and history together."""
    if db.in_transaction():
        raise RuntimeError("Inventory writes require a fresh session (no active transaction).")
    try:
        if db.get_bind().dialect.name == "sqlite":
            db.execute(text("BEGIN IMMEDIATE"))
        else:
            db.begin()
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise


def audit(db, actor, action, product_id, details):
    entry = AuditLog(actor=actor, action_type=action, product_id=product_id, details=details)
    db.add(entry)
    return entry
