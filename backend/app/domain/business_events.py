from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True)
class BusinessEvent:
    event_type: str
    operation_id: str
    business_date: date
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BusinessEffect:
    effect_type: str
    payload: dict[str, Any] = field(default_factory=dict)
