from __future__ import annotations

from terraform_drift_detection.compat import Protocol
from terraform_drift_detection.config import AzureAuthConfig
from terraform_drift_detection.config import AzureStateSourceConfig
from terraform_drift_detection.models import ResourceSnapshot


class ExpectedStateSource(Protocol):
    def load_expected_resources(self, source: AzureStateSourceConfig) -> list[ResourceSnapshot]:
        ...


class ActualInventorySource(Protocol):
    def load_actual_resources(
        self,
        expected_resources: list[ResourceSnapshot],
        subscriptions: list[str],
        auth: AzureAuthConfig,
    ) -> list[ResourceSnapshot]:
        ...
