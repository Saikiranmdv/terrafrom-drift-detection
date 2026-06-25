from __future__ import annotations

from dataclasses import dataclass

from terraform_drift_detection.config import ScannerConfig


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class DiagnosticReport:
    checks: list[DiagnosticCheck]

    @property
    def ok(self) -> bool:
        return all(item.ok for item in self.checks)


class AzureDiagnosticsRunner:
    def validate(self, config: ScannerConfig) -> DiagnosticReport:
        checks: list[DiagnosticCheck] = []
        checks.append(self._check_auth(config))
        checks.extend(self._check_blob_access(config))
        checks.append(self._check_resource_graph(config))
        checks.append(self._check_activity_logs(config))
        return DiagnosticReport(checks=checks)

    def _check_auth(self, config: ScannerConfig) -> DiagnosticCheck:
        try:
            from terraform_drift_detection.state.azure_blob_backend import _build_credential

            _build_credential(config.state_sources[0].auth)
            return DiagnosticCheck("azure_auth", True, "Azure credential object created successfully.")
        except Exception as exc:
            return DiagnosticCheck("azure_auth", False, str(exc))

    def _check_blob_access(self, config: ScannerConfig) -> list[DiagnosticCheck]:
        from terraform_drift_detection.state.azure_blob_backend import AzureBlobStateSource
        from terraform_drift_detection.state.terraform_state import TerraformStateParser

        checks: list[DiagnosticCheck] = []
        source = AzureBlobStateSource(parser=TerraformStateParser())
        for state_source in config.state_sources:
            name = f"blob_access:{state_source.name}"
            try:
                source._download_state(state_source)
                checks.append(DiagnosticCheck(name, True, "Terraform state blob is readable."))
            except Exception as exc:
                checks.append(DiagnosticCheck(name, False, str(exc)))
        return checks

    def _check_resource_graph(self, config: ScannerConfig) -> DiagnosticCheck:
        from terraform_drift_detection.models import ResourceSnapshot
        from terraform_drift_detection.providers.azure.resource_graph import AzureResourceGraphInventory

        inventory = AzureResourceGraphInventory()
        expected = [
            ResourceSnapshot(
                provider="azure",
                resource_type="microsoft.resources/subscriptions/resourcegroups",
                terraform_type="azurerm_resource_group",
                resource_id="/subscriptions/dummy/resourceGroups/dummy",
                address=None,
                name="dummy",
                location=None,
                resource_group="dummy",
                subscription_id=config.scan_scope.subscriptions[0],
                tags={},
                attributes={},
            )
        ]
        try:
            inventory.load_actual_resources(
                expected_resources=expected,
                subscriptions=config.scan_scope.subscriptions,
                auth=config.state_sources[0].auth,
            )
            return DiagnosticCheck("resource_graph", True, "Azure Resource Graph query succeeded.")
        except Exception as exc:
            return DiagnosticCheck("resource_graph", False, str(exc))

    def _check_activity_logs(self, config: ScannerConfig) -> DiagnosticCheck:
        from terraform_drift_detection.models import DriftFinding
        from terraform_drift_detection.models import DriftKind
        from terraform_drift_detection.providers.azure.activity_logs import AzureActivityLogAttributor

        attributor = AzureActivityLogAttributor()
        finding = DriftFinding(
            kind=DriftKind.CHANGED,
            resource_id=f"/subscriptions/{config.scan_scope.subscriptions[0]}/resourceGroups/dummy",
            resource_type="microsoft.resources/subscriptions/resourcegroups",
            address=None,
            changes=[],
        )
        try:
            attributor.enrich(
                [finding],
                config.scan_scope.subscriptions,
                config.scan_scope.activity_log_lookback_hours,
                config.state_sources[0].auth,
            )
            return DiagnosticCheck("activity_logs", True, "Azure Activity Log query path executed.")
        except Exception as exc:
            return DiagnosticCheck("activity_logs", False, str(exc))
