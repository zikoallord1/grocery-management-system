from uuid import uuid4

import pytest

from backend.app.core.access_control import Actor, AuthorizationError
from backend.app.core.audit_models import AuditLog
from backend.app.core.database import Base, get_session, initialize_database
from backend.app.core.identity import clear_current_actor, set_current_actor
from backend.app.core.operation_guard import authorize_operation


def test_sensitive_operation_rejection_is_audited(monkeypatch):
    initialize_database()
    session = get_session()
    token = set_current_actor(Actor(user_id=44, username="seller", role="بائع"))
    try:
        def deny(*_args, **_kwargs):
            raise AuthorizationError("لا يملك المستخدم الصلاحية المطلوبة.")

        monkeypatch.setattr("backend.app.core.operation_guard.require_permission", deny)
        operation_id = f"guard-{uuid4()}"
        with pytest.raises(AuthorizationError):
            authorize_operation(
                session,
                operation_id=operation_id,
                module="المبيعات",
                permission="إضافة",
                entity_type="SALE",
            )
        audit = session.query(AuditLog).filter_by(operation_id=operation_id).one()
        assert audit.action == "REJECT"
        assert audit.user_id == 44
        assert audit.details["result"] == "REJECTED"
    finally:
        session.rollback()
        clear_current_actor(token)
        session.close()
