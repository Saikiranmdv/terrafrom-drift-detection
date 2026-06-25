from __future__ import annotations

import unittest

from terraform_drift_detection.diff import DriftEngine
from terraform_drift_detection.models import DriftKind
from terraform_drift_detection.models import ResourceSnapshot


class DriftEngineTests(unittest.TestCase):
    def test_compare_reports_missing_unmanaged_and_changed(self) -> None:
        expected = [
            ResourceSnapshot(
                provider="azure",
                resource_type="microsoft.resources/subscriptions/resourcegroups",
                terraform_type="azurerm_resource_group",
                resource_id="/subscriptions/sub-1/resourceGroups/rg-prod",
                address="azurerm_resource_group.rg[0]",
                name="rg-prod",
                location="eastus",
                resource_group="rg-prod",
                subscription_id="sub-1",
                tags={"env": "prod"},
                attributes={"location": "eastus"},
            ),
            ResourceSnapshot(
                provider="azure",
                resource_type="microsoft.storage/storageaccounts",
                terraform_type="azurerm_storage_account",
                resource_id="/subscriptions/sub-1/resourceGroups/rg-prod/providers/Microsoft.Storage/storageAccounts/stprod001",
                address="azurerm_storage_account.sa[0]",
                name="stprod001",
                location="eastus",
                resource_group="rg-prod",
                subscription_id="sub-1",
                tags={"env": "prod"},
                attributes={"account_tier": "Standard"},
            ),
        ]
        actual = [
            ResourceSnapshot(
                provider="azure",
                resource_type="microsoft.resources/subscriptions/resourcegroups",
                terraform_type="azurerm_resource_group",
                resource_id="/subscriptions/sub-1/resourceGroups/rg-prod",
                address=None,
                name="rg-prod",
                location="eastus2",
                resource_group="rg-prod",
                subscription_id="sub-1",
                tags={"env": "prod"},
                attributes={"location": "eastus2"},
            ),
            ResourceSnapshot(
                provider="azure",
                resource_type="microsoft.network/virtualnetworks",
                terraform_type="azurerm_virtual_network",
                resource_id="/subscriptions/sub-1/resourceGroups/rg-prod/providers/Microsoft.Network/virtualNetworks/vnet-extra",
                address=None,
                name="vnet-extra",
                location="eastus",
                resource_group="rg-prod",
                subscription_id="sub-1",
                tags={},
                attributes={},
            ),
        ]

        findings = DriftEngine().compare(expected=expected, actual=actual)
        kinds = [item.kind for item in findings]

        self.assertIn(DriftKind.CHANGED, kinds)
        self.assertIn(DriftKind.MISSING_IN_CLOUD, kinds)
        self.assertIn(DriftKind.UNMANAGED_IN_CLOUD, kinds)


if __name__ == "__main__":
    unittest.main()
