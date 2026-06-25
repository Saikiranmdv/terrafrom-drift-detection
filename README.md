# Terraform Drift Detection

Azure-first Terraform drift detection tool that reads Terraform state from the `azurerm` backend in Azure Blob Storage, inventories live Azure resources, normalizes both views, and reports drift.

## Current scope

- Terraform state parsing for supported Azure resources
- Azure Blob state-source adapter
- Azure Resource Graph inventory adapter
- Provider-agnostic drift engine
- CLI entrypoint
- Architecture and backlog docs

## Supported Azure resource types in the scaffold

- `azurerm_resource_group`
- `azurerm_virtual_network`
- `azurerm_subnet`
- `azurerm_network_security_group`
- `azurerm_storage_account`
- `azurerm_linux_virtual_machine`
- `azurerm_windows_virtual_machine`

## Project layout

```text
config/
docs/
src/terraform_drift_detection/
tests/
```

## Plug And Play Setup

1. Clone the repo and create a virtual environment.
2. Run the bootstrap script:

```bash
./scripts/bootstrap.sh
```

3. Start the guided initializer:

```bash
./.venv/bin/terraform-drift init
```

If you want to run `terraform-drift` as a bare command, activate the virtual environment in your current shell first:

```bash
source .venv/bin/activate
```

For `fish`:

```fish
source .venv/bin/activate.fish
```

4. Validate config and Azure access:

```bash
./scripts/validate.sh
```

5. Run the guided end-to-end workflow:

```bash
./scripts/run-scan.sh
```

You can also run the CLI directly:

```bash
./.venv/bin/terraform-drift init --config config/azure.template.yaml
./.venv/bin/terraform-drift doctor --config config/azure.template.yaml
./.venv/bin/terraform-drift scan --config config/azure.template.yaml --json
./.venv/bin/terraform-drift explain --config config/azure.template.yaml
./.venv/bin/terraform-drift run --config config/azure.template.yaml
```

## Required User Inputs

- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `TFSTATE_STORAGE_ACCOUNT_NAME`
- `TFSTATE_CONTAINER_NAME`
- `TFSTATE_BLOB_KEY`

Optional:

- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_AUTH_MODE`
- `AI_PROVIDER`
- `AI_MODEL`
- `AI_API_KEY`
- `AI_BASE_URL`
- `ACTIVITY_LOG_LOOKBACK_HOURS`

## Azure permissions

- Terraform state backend: `Storage Blob Data Reader` or `Storage Blob Data Contributor` on the state container
- Inventory across target subscriptions: `Reader`
- Activity Log attribution: `Reader`

## Notes

- The repo is designed so a new user can clone it, set `.env`, and run it without editing Python code.
- `terraform-drift run` is the default user-facing workflow. It validates access, runs the scan, and renders an executive summary.
- `terraform-drift explain` can explain an existing JSON report or run a fresh scan and summarize it.
- Native Gemini API is supported with `AI_PROVIDER=gemini`. OpenAI-compatible providers are also supported with `AI_PROVIDER=openai_compatible`.
- The scaffold normalizes a focused set of comparable attributes for the MVP.
- Azure Resource Graph is used for broad inventory and tag/property access. Per-resource ARM fetchers can be added later for deeper diffs where Resource Graph payloads are insufficient.
- Resource groups are queried from Azure Resource Graph `ResourceContainers`, not just `Resources`, to avoid false `missing_in_cloud` results.
- If no AI provider is configured, the CLI falls back to a deterministic executive summary rather than failing.

## Common Commands

```bash
./scripts/bootstrap.sh
./scripts/validate.sh
./scripts/test.sh
./scripts/run-scan.sh
make init
make doctor
make run
```

## Troubleshooting

### `fish: Unknown command: terraform-drift`

This means the virtual environment is not active in your current shell, so `terraform-drift` is not on `PATH`.

Use:

```fish
./.venv/bin/terraform-drift run --config config/azure.template.yaml
```

or activate the environment first:

```fish
source .venv/bin/activate.fish
terraform-drift run --config config/azure.template.yaml
```

### `AI explanation unavailable from gemini: HTTP 503 Service Unavailable`

This means the Gemini request reached the provider, but the provider was temporarily unavailable or under high load.

- This is not the same as a missing `AI_PROVIDER`, `AI_MODEL`, or `AI_API_KEY`.
- The CLI falls back to the deterministic summary so the drift scan still completes.
- Retrying later is usually the correct action.
