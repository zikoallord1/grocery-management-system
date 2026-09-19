import json

import pytest

from backend.app.core.access_control import Actor, AuthorizationError, has_permission, require_permission


def test_access_control_allows_configured_permission_and_rejects_scope(tmp_path):
    path = tmp_path / "permissions.json"
    path.write_text(json.dumps({"بائع": {"المبيعات": {"إضافة": True}}}), encoding="utf-8")
    actor = Actor(user_id=4, username="seller", role="بائع", scope=frozenset({"store-a"}))
    assert has_permission(actor, module="المبيعات", permission="إضافة", resource_scope="store-a", permissions_path=path)
    with pytest.raises(AuthorizationError):
        require_permission(actor, module="المبيعات", permission="إضافة", resource_scope="store-b", permissions_path=path)


def test_access_control_enforces_segregation_of_duties(tmp_path):
    path = tmp_path / "permissions.json"
    path.write_text(json.dumps({"محاسب": {"المبيعات": {"اعتماد": True}}}), encoding="utf-8")
    actor = Actor(user_id=7, username="accountant", role="محاسب", duties=frozenset({"إنشاء"}))
    with pytest.raises(AuthorizationError, match="فصل المهام"):
        require_permission(actor, module="المبيعات", permission="اعتماد", conflicting_duty="إنشاء", permissions_path=path)
