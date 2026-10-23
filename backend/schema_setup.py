"""Create tables and upgrade the original SQLite audit enum without data loss."""
from sqlalchemy import MetaData, inspect, select
from sqlalchemy.schema import CreateTable

from .core import Base
from .models import AuditLog


def prepare_database(engine):
    if engine.dialect.name == "sqlite":
        with engine.connect() as connection:
            # SQLite DDL participates in this explicit transaction, including rollback.
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                inspector = inspect(connection)
                if inspector.has_table("audit_logs"):
                    old_checks = [item for item in inspector.get_check_constraints("audit_logs")
                                  if "action_type" in item["sqltext"]
                                  and "PRODUCT_CREATED" not in item["sqltext"]]
                    if old_checks:
                        upgrade_audit_table(connection, inspector)
                connection.commit()
            except Exception:
                connection.rollback()
                raise
    # Other SQL databases require their own enum-constraint migration if already populated.
    Base.metadata.create_all(engine)


def upgrade_audit_table(connection, inspector):
    table = AuditLog.__table__
    columns = set(table.columns.keys())
    if {column["name"] for column in inspector.get_columns("audit_logs")} != columns:
        raise RuntimeError("Unrecognized audit_logs schema; migrate it explicitly before starting the app.")
    for name in inspector.get_table_names():
        if any(fk["referred_table"] == "audit_logs" for fk in inspector.get_foreign_keys(name)):
            raise RuntimeError("Another table references audit_logs; an explicit database migration is required.")
    metadata = MetaData()
    for source in Base.metadata.sorted_tables:
        source.to_metadata(metadata)
    temporary = table.to_metadata(metadata, name="audit_logs_member1_upgrade")
    connection.execute(CreateTable(temporary))
    connection.execute(temporary.insert().from_select(list(table.columns.keys()), select(*table.columns)))
    table.drop(connection)
    connection.exec_driver_sql('ALTER TABLE "audit_logs_member1_upgrade" RENAME TO "audit_logs"')
    for index in table.indexes:
        index.create(connection)
