from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.core.database import DATA_DIR


PERMISSIONS_FILE = DATA_DIR / "permissions.json"


class AuthorizationError(PermissionError):
    """Raised when a backend operation is outside the actor's authority."""


@dataclass(frozen=True)
class Actor:
    user_id: int | None
    username: str
    role: str
    scope: frozenset[str] = frozenset()
    duties: frozenset[str] = frozenset()


def _read_permissions(path: Path = PERMISSIONS_FILE) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AuthorizationError("تعذر قراءة ملف الصلاحيات.") from exc
    return value if isinstance(value, dict) else {}


def has_permission(
    actor: Actor,
    *,
    module: str,
    permission: str,
    resource_scope: str | None = None,
    permissions_path: Path = PERMISSIONS_FILE,
) -> bool:
    if actor.role in {"admin", "مدير النظام"}:
        return True
    if resource_scope and actor.scope and resource_scope not in actor.scope:
        return False
    role_data = _read_permissions(permissions_path).get(actor.role, {})
    module_data = role_data.get(module, {}) if isinstance(role_data, dict) else {}
    return bool(isinstance(module_data, dict) and module_data.get(permission, False))


def require_permission(
    actor: Actor,
    *,
    module: str,
    permission: str,
    resource_scope: str | None = None,
    conflicting_duty: str | None = None,
    permissions_path: Path = PERMISSIONS_FILE,
) -> None:
    if conflicting_duty and conflicting_duty in actor.duties:
        raise AuthorizationError("العملية مرفوضة بسبب فصل المهام.")
    if not has_permission(
        actor,
        module=module,
        permission=permission,
        resource_scope=resource_scope,
        permissions_path=permissions_path,
    ):
        raise AuthorizationError("لا يملك المستخدم الصلاحية المطلوبة.")
