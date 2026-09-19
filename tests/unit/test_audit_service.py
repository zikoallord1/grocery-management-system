from datetime import date
from uuid import uuid4

from backend.app.core.audit_service import AuditService
from backend.app.core.database import Base, engine, get_session


def test_audit_log_is_created_and_idempotent():
    session = get_session()

    try:
        Base.metadata.create_all(bind=engine)

        operation_id = str(uuid4())

        first = AuditService(session).record(
            operation_id=operation_id,
            event_type="SALE_CONFIRMED",
            action="CREATE",
            entity_type="SALE",
            entity_id="123",
            user_id=None,
            description="اختبار تسجيل عملية البيع",
            details={
                "total": "100.00",
                "business_date": date(2026, 9, 14).isoformat(),
            },
        )

        session.commit()

        second = AuditService(session).record(
            operation_id=operation_id,
            event_type="SALE_CONFIRMED",
            action="CREATE",
            entity_type="SALE",
            entity_id="123",
        )

        assert second.id == first.id

        count = (
            AuditService(session)
            .session.query(first.__class__)
            .filter_by(operation_id=operation_id)
            .count()
        )

        assert count == 1

    finally:
        session.rollback()
        session.close()


def test_audit_failure_and_filtered_listing_are_persisted():
    session = get_session()
    try:
        Base.metadata.create_all(bind=engine)
        operation_id = str(uuid4())
        entry = AuditService(session).record_failure(
            operation_id=operation_id,
            event_type="PERMISSION_CHECK",
            action="REJECT",
            reason="غير مصرح",
            entity_type="SALE",
            entity_id="55",
            user_id=9,
        )
        session.commit()
        rows = AuditService(session).list(entity_type="SALE", entity_id=55, user_id=9)
        assert rows[0].id == entry.id
        assert rows[0].details["result"] == "REJECTED"
        assert rows[0].details["reason"] == "غير مصرح"
    finally:
        session.rollback()
        session.close()
