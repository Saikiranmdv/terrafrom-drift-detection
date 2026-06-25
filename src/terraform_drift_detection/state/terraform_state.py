from __future__ import annotations

from typing import Any

from terraform_drift_detection.models import ResourceSnapshot
from terraform_drift_detection.providers.azure.normalizers import normalize_expected_attributes
from terraform_drift_detection.providers.azure.type_map import AZURERM_TO_ARM


class TerraformStateParser:
    def parse_document(self, document: dict[str, Any]) -> list[ResourceSnapshot]:
        resources = document.get("resources") or []
        snapshots: list[ResourceSnapshot] = []

        for resource in resources:
            if resource.get("mode") != "managed":
                continue

            terraform_type = resource.get("type")
            if terraform_type not in AZURERM_TO_ARM:
                continue

            for index, instance in enumerate(resource.get("instances", []) or []):
                attributes = instance.get("attributes") or {}
                resource_id = attributes.get("id")
                if not resource_id:
                    continue

                address = _instance_address(resource, index)
                metadata = _parse_arm_resource_id(resource_id)
                snapshots.append(
                    ResourceSnapshot(
                        provider="azure",
                        resource_type=AZURERM_TO_ARM[terraform_type],
                        terraform_type=terraform_type,
                        resource_id=resource_id,
                        address=address,
                        name=attributes.get("name"),
                        location=attributes.get("location"),
                        resource_group=attributes.get("resource_group_name") or metadata["resource_group"],
                        subscription_id=metadata["subscription_id"],
                        tags=_normalize_tags(attributes),
                        attributes=normalize_expected_attributes(terraform_type, attributes),
                    )
                )

        return snapshots


def _instance_address(resource: dict[str, Any], index: int) -> str:
    module = resource.get("module")
    base = resource["type"] + "." + resource["name"]
    if module:
        return f"{module}.{base}[{index}]"
    return f"{base}[{index}]"


def _normalize_tags(attributes: dict[str, Any]) -> dict[str, str]:
    tags = attributes.get("tags_all") or attributes.get("tags") or {}
    return {str(key): str(value) for key, value in tags.items()}


def _parse_arm_resource_id(resource_id: str) -> dict[str, str | None]:
    segments = [segment for segment in resource_id.strip("/").split("/") if segment]
    subscription_id = None
    resource_group = None
    for index, segment in enumerate(segments):
        lowered = segment.lower()
        if lowered == "subscriptions" and index + 1 < len(segments):
            subscription_id = segments[index + 1]
        if lowered == "resourcegroups" and index + 1 < len(segments):
            resource_group = segments[index + 1]
    return {
        "subscription_id": subscription_id,
        "resource_group": resource_group,
    }

