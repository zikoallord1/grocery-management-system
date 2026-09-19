from __future__ import annotations

from contextvars import ContextVar

from backend.app.core.access_control import Actor, require_permission
from backend.app.core.audit_service import AuditService


_current_actor: ContextVar[Actor | None] = ContextVar("current_actor", default=None)


def actor_from_user(user: dict) -> Actor:
    raw_id = user.get("id")
    try:
        user_id = int(raw_id) if raw_id is not None else None
    except (TypeError, ValueError):
        user_id = None
    scope = user.get("scope", [])
    duties = user.get("duties", [])
    return Actor(
        user_id=user_id,
        username=str(user.get("username", "")),
        role=str(user.get("role", "")),
        scope=frozenset(str(item) for item in scope) if isinstance(scope, (list, tuple, set)) else frozenset(),
        duties=frozenset(str(item) for item in duties) if isinstance(duties, (list, tuple, set)) else frozenset(),
    )


def set_current_actor(actor: Actor):
    return _current_actor.set(actor)


def clear_current_actor(token) -> None:
    _current_actor.reset(token)


def current_actor() -> Actor:
    actor = _current_actor.get()
    if actor is None:
        raise PermissionError("لا توجد هوية مستخدم موثقة.")
    return actor


def require_current_permission(**kwargs) -> None:
    require_permission(current_actor(), **kwargs)


def audit_current_actor(session, *, operation_id: str, action: str, entity_type: str, details: dict | None = None) -> None:
    actor = current_actor()
    AuditService(session).record(
        operation_id=operation_id,
        event_type="ADMINISTRATION",
        action=action,
        entity_type=entity_type,
        user_id=actor.user_id,
        details=details or {},
    )
