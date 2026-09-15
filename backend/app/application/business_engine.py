from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from backend.app.domain.business_events import BusinessEffect, BusinessEvent
from backend.app.core.audit_service import AuditService


class BusinessEngineError(Exception):
    pass


RuleHandler = Callable[[Any, BusinessEvent], list[BusinessEffect]]
EffectHandler = Callable[[Any, BusinessEvent, BusinessEffect], None]


@dataclass(frozen=True)
class RegisteredRule:
    name: str
    event_type: str
    priority: int
    handler: RuleHandler


class BusinessEngine:
    """
    Central orchestration layer.

    Flow:
        Business Event
            -> matching Rules
            -> Effects
            -> Effect Handlers

    The engine does not commit the database transaction.
    The caller owns transaction boundaries.
    """

    def __init__(self) -> None:
        self._rules: list[RegisteredRule] = []
        self._effect_handlers: dict[str, EffectHandler] = {}

    def register_rule(
        self,
        name: str,
        event_type: str,
        handler: RuleHandler,
        priority: int = 100,
    ) -> None:
        if not name.strip():
            raise BusinessEngineError("Rule name is required")

        if not event_type.strip():
            raise BusinessEngineError("Event type is required")

        if any(rule.name == name for rule in self._rules):
            raise BusinessEngineError(f"Rule already registered: {name}")

        self._rules.append(
            RegisteredRule(
                name=name,
                event_type=event_type,
                priority=priority,
                handler=handler,
            )
        )

        self._rules.sort(key=lambda rule: (rule.priority, rule.name))

    def register_effect_handler(
        self,
        effect_type: str,
        handler: EffectHandler,
    ) -> None:
        if not effect_type.strip():
            raise BusinessEngineError("Effect type is required")

        if effect_type in self._effect_handlers:
            raise BusinessEngineError(
                f"Effect handler already registered: {effect_type}"
            )

        self._effect_handlers[effect_type] = handler

    def process(self, session: Any, event: BusinessEvent) -> list[BusinessEffect]:
        if not event.event_type.strip():
            raise BusinessEngineError("Event type is required")

        if not event.operation_id.strip():
            raise BusinessEngineError("Operation ID is required")

        rules = [
            rule
            for rule in self._rules
            if rule.event_type == event.event_type
        ]

        effects: list[BusinessEffect] = []

        for rule in rules:
            produced = rule.handler(session, event)

            if produced is None:
                continue

            if not isinstance(produced, list):
                raise BusinessEngineError(
                    f"Rule {rule.name} must return list[BusinessEffect]"
                )

            effects.extend(produced)

        for effect in effects:
            handler = self._effect_handlers.get(effect.effect_type)

            if handler is None:
                raise BusinessEngineError(
                    f"No effect handler registered: {effect.effect_type}"
                )

            handler(session, event, effect)

        if session is not None:
            AuditService(session).record(
                operation_id=event.operation_id,
                event_type=event.event_type,
                action="EVENT_PROCESSED",
                entity_type=event.payload.get("entity_type"),
                entity_id=(
                    str(event.payload["entity_id"])
                    if event.payload.get("entity_id") is not None
                    else None
                ),
                user_id=event.payload.get("created_by"),
                description=f"Business event processed: {event.event_type}",
                details=dict(event.payload),
            )

        return effects
