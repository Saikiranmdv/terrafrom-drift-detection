from __future__ import annotations

import unittest
from unittest.mock import patch

from terraform_drift_detection.config import AiConfig
from terraform_drift_detection.config import AzureAuthConfig
from terraform_drift_detection.config import AzureStateSourceConfig
from terraform_drift_detection.config import ScanScopeConfig
from terraform_drift_detection.config import ScannerConfig
from terraform_drift_detection.diagnostics.service import AzureDiagnosticsRunner


class AzureDiagnosticsRunnerTests(unittest.TestCase):
    def test_validate_aggregates_failed_checks(self) -> None:
        config = _config()
        runner = AzureDiagnosticsRunner()

        with patch.object(AzureDiagnosticsRunner, "_check_auth", return_value=runner._check_auth(config)):
            with patch.object(
                AzureDiagnosticsRunner,
                "_check_blob_access",
                return_value=[runner._check_auth(config).__class__(name="blob_access:primary", ok=False, detail="blob denied")],
            ):
                with patch.object(
                    AzureDiagnosticsRunner,
                    "_check_resource_graph",
                    return_value=runner._check_auth(config).__class__(name="resource_graph", ok=False, detail="graph denied"),
                ):
                    with patch.object(
                        AzureDiagnosticsRunner,
                        "_check_activity_logs",
                        return_value=runner._check_auth(config).__class__(name="activity_logs", ok=True, detail="ok"),
                    ):
                        report = runner.validate(config)

        self.assertEqual(4, len(report.checks))
        self.assertFalse(report.ok)

    def test_reports_missing_auth_configuration(self) -> None:
        config = ScannerConfig(
            state_sources=[
                AzureStateSourceConfig(
                    name="primary",
                    type="azurerm_backend",
                    storage_account_name="storage1",
                    container_name="tfstate",
                    key="dev.tfstate",
                    auth=AzureAuthConfig(mode="client_secret", tenant_id=None, client_id=None, client_secret=None),
                )
            ],
            scan_scope=ScanScopeConfig(subscriptions=["sub-1"], include_terraform_types=[], ignored_paths=[]),
            ai=AiConfig(),
        )

        with patch.object(AzureDiagnosticsRunner, "_check_blob_access", return_value=[]):
            with patch.object(AzureDiagnosticsRunner, "_check_resource_graph", return_value=AzureDiagnosticsRunner()._check_auth(_config())):
                with patch.object(AzureDiagnosticsRunner, "_check_activity_logs", return_value=AzureDiagnosticsRunner()._check_auth(_config())):
                    report = AzureDiagnosticsRunner().validate(config)

        self.assertFalse(report.ok)
        self.assertEqual("azure_auth", report.checks[0].name)
        self.assertFalse(report.checks[0].ok)


def _config() -> ScannerConfig:
    return ScannerConfig(
        state_sources=[
            AzureStateSourceConfig(
                name="primary",
                type="azurerm_backend",
                storage_account_name="storage1",
                container_name="tfstate",
                key="dev.tfstate",
                auth=AzureAuthConfig(mode="azure_cli", tenant_id="tenant-1"),
            )
        ],
        scan_scope=ScanScopeConfig(subscriptions=["sub-1"], include_terraform_types=[], ignored_paths=[]),
        ai=AiConfig(),
    )


if __name__ == "__main__":
    unittest.main()
