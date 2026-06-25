from __future__ import annotations


AZURERM_TO_ARM = {
    "azurerm_resource_group": "microsoft.resources/subscriptions/resourcegroups",
    "azurerm_virtual_network": "microsoft.network/virtualnetworks",
    "azurerm_subnet": "microsoft.network/virtualnetworks/subnets",
    "azurerm_network_security_group": "microsoft.network/networksecuritygroups",
    "azurerm_storage_account": "microsoft.storage/storageaccounts",
    "azurerm_linux_virtual_machine": "microsoft.compute/virtualmachines",
    "azurerm_windows_virtual_machine": "microsoft.compute/virtualmachines",
}

ARM_TO_AZURERM = {arm_type: terraform_type for terraform_type, arm_type in AZURERM_TO_ARM.items()}
