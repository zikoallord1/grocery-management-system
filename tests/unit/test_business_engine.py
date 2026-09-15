from datetime import date
from uuid import uuid4

import pytest

from backend.app.application.business_engine import (
    BusinessEngine,
    BusinessEngineError,
)
from backend.app.domain.business_events import (
    BusinessEffect,
    BusinessEvent,
)


def test_engine_processes_matching_rules_and_effects():
    engine = BusinessEngine()
    calls = []

    def rule(session, event):
        calls.append(("rule", event.operation_id))
        return [
            BusinessEffect(
                effect_type="TEST_EFFECT",
                payload={"amount": "100"},
            )
        ]

    def effect(session, event, produced):
        calls.append(
            (
                "effect",
                event.operation_id,
                produced.payload["amount"],
            )
        )

    engine.register_rule(
        name="TEST_RULE",
        event_type="SALE_CONFIRMED",
        handler=rule,
        priority=10,
    )
    engine.register_effect_handler("TEST_EFFECT", effect)

    event = BusinessEvent(
        event_type="SALE_CONFIRMED",
        operation_id=str(uuid4()),
        business_date=date(2026, 9, 14),
        payload={"sale_id": 1},
    )

    effects = engine.process(None, event)

    assert len(effects) == 1
    assert calls[0][0] == "rule"
    assert calls[1] == ("effect", event.operation_id, "100")


def test_engine_ignores_rules_for_other_events():
    engine = BusinessEngine()

    engine.register_rule(
        name="OTHER_RULE",
        event_type="PURCHASE_CONFIRMED",
        handler=lambda session, event: [
            BusinessEffect(effect_type="TEST_EFFECT")
        ],
    )

    event = BusinessEvent(
        event_type="SALE_CONFIRMED",
        operation_id=str(uuid4()),
        business_date=date(2026, 9, 14),
    )

    assert engine.process(None, event) == []


def test_duplicate_rule_name_is_rejected():
    engine = BusinessEngine()

    engine.register_rule(
        name="RULE_1",
        event_type="SALE_CONFIRMED",
        handler=lambda session, event: [],
    )

    with pytest.raises(BusinessEngineError, match="already registered"):
        engine.register_rule(
            name="RULE_1",
            event_type="PURCHASE_CONFIRMED",
            handler=lambda session, event: [],
        )


def test_missing_effect_handler_is_rejected():
    engine = BusinessEngine()

    engine.register_rule(
        name="RULE_1",
        event_type="SALE_CONFIRMED",
        handler=lambda session, event: [
            BusinessEffect(effect_type="UNKNOWN")
        ],
    )

    event = BusinessEvent(
        event_type="SALE_CONFIRMED",
        operation_id=str(uuid4()),
        business_date=date(2026, 9, 14),
    )

    with pytest.raises(
        BusinessEngineError,
        match="No effect handler registered",
    ):
        engine.process(None, event)


def test_engine_creates_audit_log_for_processed_event():
    from datetime import date
    from uuid import uuid4

    from sqlalchemy import select

    from backend.app.core.audit_models import AuditLog
    from backend.app.core.database import get_session, initialize_database

    initialize_database()
    session = get_session()

    try:
        engine = BusinessEngine()

        engine.register_rule(
            name="AUDIT_CAPTURE_RULE",
            event_type="SALE_CONFIRMED",
            handler=lambda current_session, event: [],
        )

        operation_id = str(uuid4())

        event = BusinessEvent(
            event_type="SALE_CONFIRMED",
            operation_id=operation_id,
            business_date=date(2026, 9, 14),
            payload={
                "entity_type": "SALE",
                "entity_id": 123,
                "created_by": 7,
                "total": "100.00",
            },
        )

        engine.process(session, event)

        audit = session.execute(
            select(AuditLog).where(
                AuditLog.operation_id == operation_id,
                AuditLog.event_type == "SALE_CONFIRMED",
                AuditLog.action == "EVENT_PROCESSED",
            )
        ).scalar_one_or_none()

        assert audit is not None
        assert audit.entity_type == "SALE"
        assert audit.entity_id == "123"
        assert audit.user_id == 7
        assert audit.details["total"] == "100.00"

        session.rollback()

    finally:
        session.close()
