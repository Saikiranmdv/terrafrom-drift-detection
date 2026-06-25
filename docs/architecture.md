# Architecture

## Goal

Continuously compare Terraform's expected Azure resource state with the actual live Azure environment without running `terraform plan`.

## Data flow

1. `AzureBlobStateSource` downloads a Terraform state document from the `azurerm` backend.
2. `TerraformStateParser` extracts supported `azurerm_*` resources and normalizes them into `ResourceSnapshot` objects.
3. `AzureResourceGraphInventory` queries Azure Resource Graph across configured subscriptions for the same ARM resource types.
4. Azure inventory rows are normalized into `ResourceSnapshot` objects with comparable attributes.
5. `DriftEngine` computes findings:
   - `missing_in_cloud`
   - `unmanaged_in_cloud`
   - `changed`
6. The CLI or API serializes a `DriftReport`.

## Boundaries

### Core modules

- `models.py`: shared domain objects
- `diff.py`: comparison engine
- `application/service.py`: orchestration

These modules avoid Azure SDK imports so they stay testable in isolation.

### Azure edge modules

- `state/azure_blob_backend.py`
- `providers/azure/resource_graph.py`

These are the only modules that need Azure SDK dependencies for the first slice.

## Normalization strategy

The scaffold compares a deliberately small set of stable, operator-meaningful attributes per resource type.

- Resource groups: `location`
- VNets: `location`, `address_space`, `dns_servers`
- Subnets: `address_prefixes`, `service_endpoints`
- NSGs: normalized `security_rules`
- Storage accounts: `location`, `account_tier`, `account_replication_type`, `access_tier`, `min_tls_version`, `allow_blob_public_access`
- VMs: `location`, `size`, `zone`, `network_interface_ids`

This keeps the MVP signal high and avoids false positives from provider-generated metadata.

## Next implementation step after this scaffold

Add per-resource ARM detail fetchers for the resources where Resource Graph does not expose enough fidelity for reliable attribute comparison.

