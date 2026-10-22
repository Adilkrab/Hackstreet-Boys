import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

default_file = Path(__file__).resolve().parent / "data" / "inventory.sqlite3"
url = os.getenv("WORKFLOW_DATABASE_URL", f"sqlite:///{default_file}")
if url == f"sqlite:///{default_file}":
    default_file.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    url,
    connect_args={"check_same_thread": False, "timeout": 15}
    if url.startswith("sqlite") else {},
)
if engine.dialect.name == "sqlite":
    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=15000")
        connection.execute("PRAGMA journal_mode=WAL")

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as session:
        yield session
