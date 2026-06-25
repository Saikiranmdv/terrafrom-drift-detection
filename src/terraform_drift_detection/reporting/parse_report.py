from __future__ import annotations

from datetime import datetime
from typing import Any

from terraform_drift_detection.models import AiExplanation
from terraform_drift_detection.models import DriftFinding
from terraform_drift_detection.models import DriftKind
from terraform_drift_detection.models import DriftReport
from terraform_drift_detection.models import FieldChange


def report_from_dict(payload: dict[str, Any]) -> DriftReport:
    explanation_payload = payload.get("explanation")
    explanation = None
    if isinstance(explanation_payload, dict):
        explanation = AiExplanation(
            provider=str(explanation_payload.get("provider") or "unknown"),
            model=str(explanation_payload.get("model") or "unknown"),
            summary=str(explanation_payload.get("summary") or ""),
            finding_highlights=[str(item) for item in explanation_payload.get("finding_highlights", [])],
            actor_summary=[str(item) for item in explanation_payload.get("actor_summary", [])],
            recommended_actions=[str(item) for item in explanation_payload.get("recommended_actions", [])],
            limitations=[str(item) for item in explanation_payload.get("limitations", [])],
        )

    findings: list[DriftFinding] = []
    for item in payload.get("findings", []):
        changes = [
            FieldChange(path=str(change["path"]), expected=change.get("expected"), actual=change.get("actual"))
            for change in item.get("changes", [])
        ]
        findings.append(
            DriftFinding(
                kind=DriftKind(item["kind"]),
                resource_id=str(item["resource_id"]),
                resource_type=str(item["resource_type"]),
                address=item.get("address"),
                changes=changes,
                changed_by=item.get("changed_by"),
                changed_at=item.get("changed_at"),
                change_operation=item.get("change_operation"),
            )
        )

    return DriftReport(
        scan_id=str(payload["scan_id"]),
        started_at=datetime.fromisoformat(payload["started_at"]),
        finished_at=datetime.fromisoformat(payload["finished_at"]),
        findings=findings,
        explanation=explanation,
    )
