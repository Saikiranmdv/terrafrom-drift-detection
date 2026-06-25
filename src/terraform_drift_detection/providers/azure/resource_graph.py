from __future__ import annotations

from typing import Any

from terraform_drift_detection.config import AzureAuthConfig
from terraform_drift_detection.models import ResourceSnapshot
from terraform_drift_detection.providers.azure.normalizers import normalize_actual_attributes
from terraform_drift_detection.providers.azure.type_map import ARM_TO_AZURERM
from terraform_drift_detection.providers.azure.type_map import AZURERM_TO_ARM
from terraform_drift_detection.state.azure_blob_backend import _build_credential


class AzureResourceGraphInventory:
    def load_actual_resources(
        self,
        expected_resources: list[ResourceSnapshot],
        subscriptions: list[str],
        auth: AzureAuthConfig,
    ) -> list[ResourceSnapshot]:
        if not subscriptions:
            raise ValueError("At least one subscription is required for Azure Resource Graph queries.")

        resource_types = sorted({item.resource_type for item in expected_resources if item.resource_type})
        if not resource_types:
            return []

        rows = self._query_resource_graph(subscriptions=subscriptions, resource_types=resource_types, auth=auth)
        snapshots: list[ResourceSnapshot] = []
        for row in rows:
            snapshot = self._to_snapshot(row)
            if snapshot.resource_id:
                snapshots.append(snapshot)
        return snapshots

    def _query_resource_graph(
        self,
        subscriptions: list[str],
        resource_types: list[str],
        auth: AzureAuthConfig,
    ) -> list[dict[str, Any]]:
        try:
            from azure.mgmt.resourcegraph import ResourceGraphClient
            from azure.mgmt.resourcegraph.models import QueryRequest
        except ImportError as exc:
            raise RuntimeError("Install the 'azure' optional dependency to query Azure Resource Graph.") from exc

        credential = _build_credential(auth)
        client = ResourceGraphClient(credential=credential)
        rows: list[dict[str, Any]] = []
        rows.extend(self._query_resources_table(client, QueryRequest, subscriptions, resource_types))
        if AZURERM_TO_ARM["azurerm_resource_group"] in resource_types:
            rows.extend(self._query_resource_containers_table(client, QueryRequest, subscriptions))
        return rows

    def _query_resources_table(
        self,
        client: Any,
        query_request_type: Any,
        subscriptions: list[str],
        resource_types: list[str],
    ) -> list[dict[str, Any]]:
        non_container_types = [
            item for item in resource_types if item != AZURERM_TO_ARM["azurerm_resource_group"]
        ]
        if not non_container_types:
            return []
        type_filter = ", ".join(f"'{item}'" for item in non_container_types)
        query = (
            "Resources "
            f"| where type in~ ({type_filter}) "
            "| project id, name, type, location, resourceGroup, subscriptionId, tags, properties, sku, zones"
        )
        request = query_request_type(subscriptions=subscriptions, query=query)
        response = client.resources(request)
        data = response.data or []
        if isinstance(data, list):
            return data
        return []

    def _query_resource_containers_table(
        self,
        client: Any,
        query_request_type: Any,
        subscriptions: list[str],
    ) -> list[dict[str, Any]]:
        query = (
            "ResourceContainers "
            "| where type =~ 'microsoft.resources/subscriptions/resourcegroups' "
            "| project id, name, type, location, resourceGroup=name, subscriptionId, tags, properties=pack_all(), sku=dynamic(null), zones=dynamic(null)"
        )
        request = query_request_type(subscriptions=subscriptions, query=query)
        response = client.resources(request)
        data = response.data or []
        if isinstance(data, list):
            return data
        return []

    def _to_snapshot(self, row: dict[str, Any]) -> ResourceSnapshot:
        resource_type = _normalize_resource_type(row.get("type"))
        resource_id = row["id"]
        tags = row.get("tags") or {}
        return ResourceSnapshot(
            provider="azure",
            resource_type=resource_type,
            terraform_type=ARM_TO_AZURERM.get(resource_type),
            resource_id=resource_id,
            address=None,
            name=row.get("name"),
            location=row.get("location"),
            resource_group=row.get("resourceGroup"),
            subscription_id=row.get("subscriptionId"),
            tags={str(key): str(value) for key, value in tags.items()},
            attributes=normalize_actual_attributes(resource_type, row),
        )


def _normalize_resource_type(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().lower()
