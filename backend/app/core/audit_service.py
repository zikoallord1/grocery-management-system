from typing import Any

from sqlalchemy import select

from backend.app.core.audit_models import AuditLog


class AuditService:
    def __init__(self, session):
        self.session = session

    def record(
        self,
        *,
        operation_id: str,
        event_type: str,
        action: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        user_id: int | None = None,
        description: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        if not operation_id.strip():
            raise ValueError("operation_id is required")

        if not event_type.strip():
            raise ValueError("event_type is required")

        if not action.strip():
            raise ValueError("action is required")

        existing = self.session.execute(
            select(AuditLog).where(
                AuditLog.operation_id == operation_id,
                AuditLog.event_type == event_type,
                AuditLog.action == action,
            )
        ).scalar_one_or_none()

        if existing is not None:
            return existing

        entry = AuditLog(
            operation_id=operation_id,
            event_type=event_type,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            description=description,
            details=details,
        )

        self.session.add(entry)
        self.session.flush()

        return entry

    def record_failure(
        self,
        *,
        operation_id: str,
        event_type: str,
        action: str,
        reason: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        user_id: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> AuditLog:
        payload = dict(details or {})
        payload["result"] = "REJECTED"
        payload["reason"] = reason
        return self.record(
            operation_id=operation_id,
            event_type=event_type,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            description=reason,
            details=payload,
        )

    def list(
        self,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        user_id: int | None = None,
        limit: int = 500,
    ) -> list[AuditLog]:
        if limit < 1 or limit > 5000:
            raise ValueError("limit must be between 1 and 5000")
        statement = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit)
        if entity_type is not None:
            statement = statement.where(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            statement = statement.where(AuditLog.entity_id == str(entity_id))
        if user_id is not None:
            statement = statement.where(AuditLog.user_id == user_id)
        return list(self.session.execute(statement).scalars())
