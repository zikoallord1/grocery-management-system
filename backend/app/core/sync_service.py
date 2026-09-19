from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.audit_service import AuditService
from backend.app.core.sync_models import SyncTransaction


SYNC_STATES = frozenset({"PENDING", "SYNCING", "SYNCED", "FAILED", "RETRY", "EXCEPTION", "REJECTED", "POSTED", "LOCKED"})


class SyncError(RuntimeError):
    pass


class AlreadyPostedError(SyncError):
    pass


class SyncService:
    def __init__(self, session: Session):
        self.session = session

    def receive(
        self,
        *,
        source_transaction_id: str,
        idempotency_key: str,
        document_type: str,
        payload: dict[str, Any] | None = None,
        temp_number: str | None = None,
        created_by: int | None = None,
    ) -> SyncTransaction:
        if not source_transaction_id.strip() or not idempotency_key.strip():
            raise SyncError("source_transaction_id و idempotency_key مطلوبان.")
        existing_key = self.session.execute(
            select(SyncTransaction).where(SyncTransaction.idempotency_key == idempotency_key)
        ).scalar_one_or_none()
        if existing_key is not None:
            return existing_key
        existing_source = self.session.execute(
            select(SyncTransaction).where(SyncTransaction.source_transaction_id == source_transaction_id)
        ).scalar_one_or_none()
        if existing_source is not None:
            if existing_source.state in {"POSTED", "LOCKED"}:
                raise AlreadyPostedError("ALREADY_POSTED")
            raise SyncError("المعاملة المصدر موجودة بمفتاح idempotency مختلف.")
        transaction = SyncTransaction(
            source_transaction_id=source_transaction_id,
            idempotency_key=idempotency_key,
            document_type=document_type,
            state="PENDING",
            temp_number=temp_number,
            created_by=created_by,
            payload=payload or {},
            server_received_at=datetime.now(timezone.utc),
        )
        self.session.add(transaction)
        self.session.flush()
        self._audit(transaction, "SYNC_RECEIVED")
        return transaction

    def transition(self, transaction_id: int, state: str) -> SyncTransaction:
        if state not in SYNC_STATES:
            raise SyncError(f"حالة مزامنة غير مدعومة: {state}")
        transaction = self._get(transaction_id)
        allowed = {
            "PENDING": {"SYNCING", "REJECTED", "FAILED", "EXCEPTION"},
            "SYNCING": {"SYNCED", "RETRY", "FAILED", "EXCEPTION", "REJECTED"},
            "RETRY": {"SYNCING", "REJECTED", "FAILED", "EXCEPTION"},
            "SYNCED": {"POSTED", "REJECTED"},
            "POSTED": {"LOCKED"},
            "FAILED": {"RETRY", "EXCEPTION", "REJECTED"},
            "EXCEPTION": {"RETRY", "REJECTED"},
            "REJECTED": set(),
            "LOCKED": set(),
        }
        if state != transaction.state and state not in allowed.get(transaction.state, set()):
            raise SyncError(f"لا يمكن نقل المعاملة من {transaction.state} إلى {state}.")
        transaction.state = state
        self._audit(transaction, f"SYNC_{state}")
        return transaction

    def finalize_settlement(self, transaction_id: int, accepted_by: int) -> SyncTransaction:
        transaction = self._get(transaction_id)
        if transaction.state != "SYNCED":
            raise SyncError("لا يمكن اعتماد التسوية قبل SYNCED.")
        if transaction.created_by is not None and transaction.created_by == accepted_by:
            raise SyncError("فصل المهام يمنع اعتماد المستخدم لمنشأ معاملته.")
        transaction.settlement_status = "FINALIZED"
        transaction.accepted_by = accepted_by
        self._audit(transaction, "SETTLEMENT_FINALIZED")
        return transaction

    def post(self, transaction_id: int, final_number: str) -> SyncTransaction:
        transaction = self._get(transaction_id)
        if transaction.state in {"POSTED", "LOCKED"}:
            return transaction
        if transaction.state != "SYNCED" or transaction.settlement_status != "FINALIZED":
            raise SyncError("الترحيل يتطلب SYNCED وتسوية FINALIZED.")
        if not final_number.strip():
            raise SyncError("final_number مطلوب عند الترحيل.")
        transaction.final_number = final_number
        transaction.state = "POSTED"
        transaction.version += 1
        self._audit(transaction, "POSTED")
        return transaction

    def reverse(self, transaction_id: int, *, idempotency_key: str, created_by: int | None = None) -> SyncTransaction:
        original = self._get(transaction_id)
        if original.state not in {"POSTED", "LOCKED"}:
            raise SyncError("لا يمكن عكس معاملة غير مرحلة.")
        existing = self.session.execute(
            select(SyncTransaction).where(SyncTransaction.idempotency_key == idempotency_key)
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        reversal = self.receive(
            source_transaction_id=f"{original.source_transaction_id}:REV:{uuid4().hex}",
            idempotency_key=idempotency_key,
            document_type=f"REVERSE_{original.document_type}",
            payload={"reverses_transaction_id": original.id},
            created_by=created_by,
        )
        original.reversed_transaction_id = reversal.id
        self._audit(original, "REVERSE_CREATED", details={"reversal_id": reversal.id})
        return reversal

    def _get(self, transaction_id: int) -> SyncTransaction:
        transaction = self.session.get(SyncTransaction, transaction_id)
        if transaction is None:
            raise SyncError("المعاملة غير موجودة.")
        return transaction

    def _audit(self, transaction: SyncTransaction, action: str, details: dict[str, Any] | None = None) -> None:
        AuditService(self.session).record(
            operation_id=transaction.idempotency_key,
            event_type="SYNC_TRANSACTION",
            action=action,
            entity_type=transaction.document_type,
            entity_id=str(transaction.id),
            user_id=transaction.created_by,
            details={"state": transaction.state, **(details or {})},
        )
