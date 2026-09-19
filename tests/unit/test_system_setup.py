import pytest

from backend.app.core.access_control import Actor, AuthorizationError
from backend.app.core.demo_data import prepare_for_delivery


def test_system_initialization_requires_admin_and_explicit_confirmation():
    with pytest.raises(AuthorizationError):
        prepare_for_delivery()
    actor = Actor(user_id=1, username="manager", role="مدير")
    with pytest.raises(AuthorizationError):
        prepare_for_delivery(actor=actor, confirmation="تهيئة النظام")
