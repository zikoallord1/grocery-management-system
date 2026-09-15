from sqlalchemy import event

from backend.app.core.audit_models import AuditLog
from backend.app.core.database import Base, engine


def initialize_audit_tables() -> None:
    Base.metadata.create_all(bind=engine, tables=[AuditLog.__table__])


@event.listens_for(engine, "connect")
def _enable_audit_setup(dbapi_connection, connection_record):
    # Database initialization remains controlled by initialize_database().
    # This hook intentionally does not mutate application data.
    return None
