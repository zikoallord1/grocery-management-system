import pytest

from backend.app.core.assistant_service import AssistantService


def test_assistant_explains_errors_without_mutating_data():
    assistant = AssistantService()
    result = assistant.diagnose("Duplicate idempotency key")
    assert result["read_only"] is True
    assert "idempotency" in result["advice"]
    with pytest.raises(PermissionError):
        assistant.execute_change("delete", "sale")
