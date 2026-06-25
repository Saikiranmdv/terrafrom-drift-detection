from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class DriftKind(str, Enum):
    MISSING_IN_CLOUD = "missing_in_cloud"
    UNMANAGED_IN_CLOUD = "unmanaged_in_cloud"
    CHANGED = "changed"


@dataclass(frozen=True)
class ResourceSnapshot:
    provider: str
    resource_type: str
    terraform_type: str | None
    resource_id: str
    address: str | None
    name: str | None
    location: str | None
    resource_group: str | None
    subscription_id: str | None
    tags: dict[str, str]
    attributes: dict[str, Any]


@dataclass(frozen=True)
class FieldChange:
    path: str
    expected: Any
    actual: Any


@dataclass(frozen=True)
class DriftFinding:
    kind: DriftKind
    resource_id: str
    resource_type: str
    address: str | None
    changes: list[FieldChange]
    changed_by: str | None = None
    changed_at: str | None = None
    change_operation: str | None = None


@dataclass(frozen=True)
class AiExplanation:
    provider: str
    model: str
    summary: str
    finding_highlights: list[str]
    actor_summary: list[str]
    recommended_actions: list[str]
    limitations: list[str]


@dataclass(frozen=True)
class DriftReport:
    scan_id: str
    started_at: datetime
    finished_at: datetime
    findings: list[DriftFinding]
    explanation: AiExplanation | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["started_at"] = self.started_at.isoformat()
        payload["finished_at"] = self.finished_at.isoformat()
        return payload
