from __future__ import annotations

from typing import Any

from terraform_drift_detection.providers.azure.type_map import AZURERM_TO_ARM


def normalize_expected_attributes(terraform_type: str, attributes: dict[str, Any]) -> dict[str, Any]:
    if terraform_type == "azurerm_resource_group":
        return {"location": attributes.get("location")}

    if terraform_type == "azurerm_virtual_network":
        return {
            "location": attributes.get("location"),
            "address_space": sorted(attributes.get("address_space", []) or []),
            "dns_servers": sorted(attributes.get("dns_servers", []) or []),
        }

    if terraform_type == "azurerm_subnet":
        prefixes = attributes.get("address_prefixes")
        if prefixes is None and attributes.get("address_prefix"):
            prefixes = [attributes["address_prefix"]]
        return {
            "address_prefixes": sorted(prefixes or []),
            "service_endpoints": sorted(attributes.get("service_endpoints", []) or []),
        }

    if terraform_type == "azurerm_network_security_group":
        return {
            "location": attributes.get("location"),
            "security_rules": _normalize_nsg_rules(attributes.get("security_rule", []) or []),
        }

    if terraform_type == "azurerm_storage_account":
        return {
            "location": attributes.get("location"),
            "account_tier": attributes.get("account_tier"),
            "account_replication_type": attributes.get("account_replication_type"),
            "access_tier": attributes.get("access_tier"),
            "min_tls_version": attributes.get("min_tls_version"),
            "allow_blob_public_access": attributes.get("allow_blob_public_access"),
        }

    if terraform_type in {"azurerm_linux_virtual_machine", "azurerm_windows_virtual_machine"}:
        zone = attributes.get("zone")
        if zone is None and attributes.get("zones"):
            zone = attributes["zones"]
        return {
            "location": attributes.get("location"),
            "size": attributes.get("size") or attributes.get("vm_size"),
            "zone": zone,
            "network_interface_ids": sorted(attributes.get("network_interface_ids", []) or []),
        }

    return {}


def normalize_actual_attributes(resource_type: str, row: dict[str, Any]) -> dict[str, Any]:
    properties = row.get("properties", {}) or {}

    if resource_type == AZURERM_TO_ARM["azurerm_resource_group"]:
        return {"location": row.get("location")}

    if resource_type == AZURERM_TO_ARM["azurerm_virtual_network"]:
        address_space = (((properties.get("addressSpace") or {}).get("addressPrefixes")) or [])
        dns_servers = (((properties.get("dhcpOptions") or {}).get("dnsServers")) or [])
        return {
            "location": row.get("location"),
            "address_space": sorted(address_space),
            "dns_servers": sorted(dns_servers),
        }

    if resource_type == AZURERM_TO_ARM["azurerm_subnet"]:
        prefixes = properties.get("addressPrefixes")
        if prefixes is None and properties.get("addressPrefix"):
            prefixes = [properties["addressPrefix"]]
        endpoints = []
        for item in properties.get("serviceEndpoints", []) or []:
            service_name = item.get("service")
            if service_name:
                endpoints.append(service_name)
        return {
            "address_prefixes": sorted(prefixes or []),
            "service_endpoints": sorted(endpoints),
        }

    if resource_type == AZURERM_TO_ARM["azurerm_network_security_group"]:
        return {
            "location": row.get("location"),
            "security_rules": _normalize_nsg_rules(properties.get("securityRules", []) or []),
        }

    if resource_type == AZURERM_TO_ARM["azurerm_storage_account"]:
        sku = row.get("sku", {}) or {}
        tier = sku.get("tier")
        replication = None
        sku_name = sku.get("name")
        if isinstance(sku_name, str) and "_" in sku_name:
            _, replication = sku_name.split("_", 1)
        return {
            "location": row.get("location"),
            "account_tier": tier,
            "account_replication_type": replication,
            "access_tier": properties.get("accessTier"),
            "min_tls_version": properties.get("minimumTlsVersion"),
            "allow_blob_public_access": properties.get("allowBlobPublicAccess"),
        }

    if resource_type == AZURERM_TO_ARM["azurerm_linux_virtual_machine"] or resource_type == AZURERM_TO_ARM["azurerm_windows_virtual_machine"]:
        nic_ids = []
        network_interfaces = (((properties.get("networkProfile") or {}).get("networkInterfaces")) or [])
        for item in network_interfaces:
            nic_id = item.get("id")
            if nic_id:
                nic_ids.append(nic_id)
        zones = row.get("zones") or []
        zone: str | list[str] | None
        if not zones:
            zone = None
        elif len(zones) == 1:
            zone = zones[0]
        else:
            zone = zones
        return {
            "location": row.get("location"),
            "size": (((properties.get("hardwareProfile") or {}).get("vmSize"))),
            "zone": zone,
            "network_interface_ids": sorted(nic_ids),
        }

    return {}


def _normalize_nsg_rules(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for rule in rules:
        source = rule.get("source_address_prefix") or rule.get("sourceAddressPrefix")
        destination = rule.get("destination_address_prefix") or rule.get("destinationAddressPrefix")
        source_ports = rule.get("source_port_ranges") or rule.get("sourcePortRanges")
        if source_ports is None:
            source_ports = [rule.get("source_port_range") or rule.get("sourcePortRange")]
        destination_ports = rule.get("destination_port_ranges") or rule.get("destinationPortRanges")
        if destination_ports is None:
            destination_ports = [rule.get("destination_port_range") or rule.get("destinationPortRange")]
        normalized.append(
            {
                "name": rule.get("name"),
                "priority": rule.get("priority"),
                "direction": rule.get("direction"),
                "access": rule.get("access"),
                "protocol": rule.get("protocol"),
                "source": source,
                "destination": destination,
                "source_ports": sorted([item for item in source_ports if item]),
                "destination_ports": sorted([item for item in destination_ports if item]),
            }
        )
    return sorted(normalized, key=lambda item: (item["priority"] or 0, item["name"] or ""))

