from __future__ import annotations

import unittest

from terraform_drift_detection.providers.azure.resource_graph import AzureResourceGraphInventory


class AzureResourceGraphInventoryTests(unittest.TestCase):
    def test_to_snapshot_handles_resource_group_container_type(self) -> None:
        row = {
            "id": "/subscriptions/sub-1/resourceGroups/rg-prod",
            "name": "rg-prod",
            "type": "microsoft.resources/subscriptions/resourcegroups",
            "location": "eastus",
            "resourceGroup": "rg-prod",
            "subscriptionId": "sub-1",
            "tags": {"env": "prod"},
            "properties": {},
        }

        snapshot = AzureResourceGraphInventory()._to_snapshot(row)

        self.assertEqual("azurerm_resource_group", snapshot.terraform_type)
        self.assertEqual("microsoft.resources/subscriptions/resourcegroups", snapshot.resource_type)


if __name__ == "__main__":
    unittest.main()
