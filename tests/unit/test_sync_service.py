import pytest
from uuid import uuid4

from backend.app.core.database import Base, engine, get_session, initialize_database
from backend.app.core.identity import actor_from_user, clear_current_actor, current_actor, set_current_actor
from backend.app.core.sync_service import AlreadyPostedError, SyncError, SyncService


def test_sync_idempotency_posting_and_reversal():
    initialize_database()
    Base.metadata.create_all(bind=engine)
    session = get_session()
    try:
        service = SyncService(session)
        suffix = uuid4().hex
        first = service.receive(
            source_transaction_id=f"offline-1-{suffix}",
            idempotency_key=f"idem-1-{suffix}",
            document_type="SALE",
            temp_number="TMP-1",
            created_by=10,
        )
        assert service.receive(
            source_transaction_id=f"offline-ignored-{suffix}",
            idempotency_key=f"idem-1-{suffix}",
            document_type="SALE",
        ).id == first.id
        service.transition(first.id, "SYNCING")
        service.transition(first.id, "SYNCED")
        service.finalize_settlement(first.id, accepted_by=11)
        service.post(first.id, "S-100")
        assert first.state == "POSTED"
        assert first.version == 1
        with pytest.raises(AlreadyPostedError, match="ALREADY_POSTED"):
            service.receive(
                source_transaction_id=f"offline-1-{suffix}",
                idempotency_key=f"idem-2-{suffix}",
                document_type="SALE",
            )
        reversal = service.reverse(first.id, idempotency_key=f"idem-reversal-{suffix}", created_by=11)
        assert reversal.document_type == "REVERSE_SALE"
        assert first.state == "POSTED"
        session.commit()
    finally:
        session.rollback()
        session.close()


def test_sync_requires_settlement_and_segregation_of_duties():
    initialize_database()
    session = get_session()
    try:
        service = SyncService(session)
        suffix = uuid4().hex
        transaction = service.receive(
            source_transaction_id=f"offline-2-{suffix}",
            idempotency_key=f"idem-3-{suffix}",
            document_type="PURCHASE",
            created_by=20,
        )
        service.transition(transaction.id, "SYNCING")
        service.transition(transaction.id, "SYNCED")
        with pytest.raises(SyncError):
            service.finalize_settlement(transaction.id, accepted_by=20)
        with pytest.raises(SyncError):
            service.post(transaction.id, "P-100")
    finally:
        session.rollback()
        session.close()


def test_identity_context_is_wired_from_login_user():
    token = set_current_actor(actor_from_user({"id": "7", "username": "بائع", "role": "بائع", "scope": ["store-a"]}))
    try:
        assert current_actor().user_id == 7
        assert "store-a" in current_actor().scope
    finally:
        clear_current_actor(token)
