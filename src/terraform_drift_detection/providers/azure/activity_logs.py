from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from datetime import timedelta
from typing import Any

from terraform_drift_detection.config import AzureAuthConfig
from terraform_drift_detection.models import DriftFinding
from terraform_drift_detection.state.azure_blob_backend import _build_credential


class AzureActivityLogAttributor:
    def enrich(
        self,
        findings: list[DriftFinding],
        subscriptions: list[str],
        lookback_hours: int,
        auth: AzureAuthConfig,
    ) -> list[DriftFinding]:
        if not findings:
            return findings

        try:
            from azure.mgmt.monitor import MonitorManagementClient
        except ImportError:
            return findings
        except Exception:
            return findings

        lookback_start = datetime.utcnow() - timedelta(hours=lookback_hours)
        credential = _build_credential(auth)
        clients = {
            subscription_id: MonitorManagementClient(credential=credential, subscription_id=subscription_id)
            for subscription_id in subscriptions
        }

        enriched: list[DriftFinding] = []
        for finding in findings:
            subscription_id = _subscription_from_resource_id(finding.resource_id)
            client = clients.get(subscription_id)
            if not client:
                enriched.append(finding)
                continue
            event = _latest_event_for_resource(client, finding.resource_id, lookback_start)
            if not event:
                enriched.append(finding)
                continue
            enriched.append(
                replace(
                    finding,
                    changed_by=_extract_caller(event),
                    changed_at=_extract_event_time(event),
                    change_operation=_extract_operation(event),
                )
            )
        return enriched


def _latest_event_for_resource(client: Any, resource_id: str, lookback_start: datetime) -> Any | None:
    timestamp = lookback_start.strftime("%Y-%m-%dT%H:%M:%SZ")
    filter_clause = f"eventTimestamp ge '{timestamp}' and resourceUri eq '{resource_id}'"
    try:
        events = client.activity_logs.list(filter=filter_clause)
    except Exception:
        return None

    latest = None
    latest_timestamp = None
    for event in events:
        operation = _extract_operation(event) or ""
        if not _is_relevant_operation(operation):
            continue
        event_time = getattr(event, "event_timestamp", None)
        if latest is None or (event_time and latest_timestamp and event_time > latest_timestamp) or (event_time and latest_timestamp is None):
            latest = event
            latest_timestamp = event_time
    return latest


def _extract_caller(event: Any) -> str | None:
    caller = getattr(event, "caller", None)
    if caller:
        return str(caller)
    claims = getattr(event, "claims", None) or {}
    for key in ("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn", "appid", "name"):
        value = claims.get(key)
        if value:
            return str(value)
    return None


def _extract_event_time(event: Any) -> str | None:
    event_time = getattr(event, "event_timestamp", None)
    if event_time is None:
        return None
    try:
        return event_time.isoformat()
    except Exception:
        return str(event_time)


def _extract_operation(event: Any) -> str | None:
    operation_name = getattr(event, "operation_name", None)
    value = getattr(operation_name, "value", None)
    if value:
        return str(value)
    localized = getattr(operation_name, "localized_value", None)
    if localized:
        return str(localized)
    return None


def _is_relevant_operation(operation: str) -> bool:
    lowered = operation.lower()
    return "/write" in lowered or "/delete" in lowered or "delete" in lowered or "write" in lowered


def _subscription_from_resource_id(resource_id: str) -> str | None:
    segments = [segment for segment in resource_id.strip("/").split("/") if segment]
    for index, segment in enumerate(segments):
        if segment.lower() == "subscriptions" and index + 1 < len(segments):
            return segments[index + 1]
    return None
