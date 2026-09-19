from __future__ import annotations

from backend.app.core.access_control import AuthorizationError, require_permission
from backend.app.core.audit_service import AuditService
from backend.app.core.identity import _current_actor


def authorize_operation(
    session,
    *,
    operation_id: str,
    module: str,
    permission: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    created_by: int | None = None,
) -> int | None:
    actor = _current_actor.get()
    if actor is None:
        return created_by
    try:
        require_permission(actor, module=module, permission=permission)
    except AuthorizationError as exc:
        AuditService(session).record_failure(
            operation_id=operation_id,
            event_type="AUTHORIZATION",
            action="REJECT",
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=actor.user_id,
            reason=str(exc),
            details={"module": module, "permission": permission},
        )
        raise
    return actor.user_id
