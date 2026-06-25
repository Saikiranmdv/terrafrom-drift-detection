from __future__ import annotations

from typing import Any

from terraform_drift_detection.models import DriftFinding
from terraform_drift_detection.models import DriftKind
from terraform_drift_detection.models import FieldChange
from terraform_drift_detection.models import ResourceSnapshot


class DriftEngine:
    def compare(
        self,
        expected: list[ResourceSnapshot],
        actual: list[ResourceSnapshot],
        ignored_paths: list[str] | None = None,
    ) -> list[DriftFinding]:
        ignored = ignored_paths or []
        findings: list[DriftFinding] = []

        expected_by_id = {_normalize_id(item.resource_id): item for item in expected}
        actual_by_id = {_normalize_id(item.resource_id): item for item in actual}

        for resource_id in sorted(expected_by_id.keys() - actual_by_id.keys()):
            resource = expected_by_id[resource_id]
            findings.append(
                DriftFinding(
                    kind=DriftKind.MISSING_IN_CLOUD,
                    resource_id=resource.resource_id,
                    resource_type=resource.resource_type,
                    address=resource.address,
                    changes=[],
                )
            )

        for resource_id in sorted(actual_by_id.keys() - expected_by_id.keys()):
            resource = actual_by_id[resource_id]
            findings.append(
                DriftFinding(
                    kind=DriftKind.UNMANAGED_IN_CLOUD,
                    resource_id=resource.resource_id,
                    resource_type=resource.resource_type,
                    address=resource.address,
                    changes=[],
                )
            )

        for resource_id in sorted(expected_by_id.keys() & actual_by_id.keys()):
            expected_resource = expected_by_id[resource_id]
            actual_resource = actual_by_id[resource_id]
            changes = _collect_changes(expected_resource, actual_resource, ignored)
            if changes:
                findings.append(
                    DriftFinding(
                        kind=DriftKind.CHANGED,
                        resource_id=expected_resource.resource_id,
                        resource_type=expected_resource.resource_type,
                        address=expected_resource.address,
                        changes=changes,
                    )
                )

        return findings


def _collect_changes(
    expected: ResourceSnapshot,
    actual: ResourceSnapshot,
    ignored_paths: list[str],
) -> list[FieldChange]:
    changes: list[FieldChange] = []
    changes.extend(_diff_mapping("tags", expected.tags, actual.tags, ignored_paths))
    changes.extend(_diff_value("", expected.attributes, actual.attributes, ignored_paths))
    return changes


def _diff_mapping(
    prefix: str,
    expected: dict[str, Any],
    actual: dict[str, Any],
    ignored_paths: list[str],
) -> list[FieldChange]:
    changes: list[FieldChange] = []
    for key in sorted(set(expected) | set(actual)):
        path = f"{prefix}.{key}"
        if _is_ignored(path, ignored_paths):
            continue
        if expected.get(key) != actual.get(key):
            changes.append(FieldChange(path=path, expected=expected.get(key), actual=actual.get(key)))
    return changes


def _diff_value(
    path: str,
    expected: Any,
    actual: Any,
    ignored_paths: list[str],
) -> list[FieldChange]:
    if _is_ignored(path, ignored_paths):
        return []

    if isinstance(expected, dict) and isinstance(actual, dict):
        changes: list[FieldChange] = []
        for key in sorted(set(expected) | set(actual)):
            child_path = key if not path else f"{path}.{key}"
            changes.extend(_diff_value(child_path, expected.get(key), actual.get(key), ignored_paths))
        return changes

    if isinstance(expected, list) and isinstance(actual, list):
        if expected == actual:
            return []
        return [FieldChange(path=path, expected=expected, actual=actual)]

    if expected != actual:
        return [FieldChange(path=path, expected=expected, actual=actual)]
    return []


def _is_ignored(path: str, ignored_paths: list[str]) -> bool:
    if not path:
        return False
    for ignored in ignored_paths:
        if ignored.endswith("[*]"):
            prefix = ignored[:-3]
            if path.startswith(prefix):
                return True
        if path == ignored or path.startswith(f"{ignored}."):
            return True
    return False


def _normalize_id(resource_id: str) -> str:
    return resource_id.strip().lower()

