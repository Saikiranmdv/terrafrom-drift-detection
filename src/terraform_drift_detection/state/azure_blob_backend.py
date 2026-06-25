from __future__ import annotations

import json
from typing import Any

from terraform_drift_detection.config import AzureAuthConfig
from terraform_drift_detection.config import AzureStateSourceConfig
from terraform_drift_detection.models import ResourceSnapshot
from terraform_drift_detection.state.terraform_state import TerraformStateParser


class AzureBlobStateSource:
    def __init__(self, parser: TerraformStateParser) -> None:
        self._parser = parser

    def load_expected_resources(self, source: AzureStateSourceConfig) -> list[ResourceSnapshot]:
        document = self._download_state(source)
        return self._parser.parse_document(document)

    def _download_state(self, source: AzureStateSourceConfig) -> dict[str, Any]:
        try:
            from azure.storage.blob import BlobClient
        except ImportError as exc:
            raise RuntimeError("Install the 'azure' optional dependency to read Terraform state from Azure Blob Storage.") from exc

        credential = _build_credential(source.auth)
        account_url = f"https://{source.storage_account_name}.blob.core.windows.net"
        client = BlobClient(
            account_url=account_url,
            container_name=source.container_name,
            blob_name=source.key,
            credential=credential,
        )
        payload = client.download_blob().readall()
        return json.loads(payload)


def _build_credential(auth: AzureAuthConfig):
    try:
        from azure.identity import AzureCliCredential
        from azure.identity import ClientSecretCredential
        from azure.identity import DefaultAzureCredential
        from azure.identity import ManagedIdentityCredential
    except ImportError as exc:
        raise RuntimeError("Install the 'azure' optional dependency to authenticate to Azure.") from exc

    if auth.mode == "client_secret":
        if not auth.tenant_id or not auth.client_id or not auth.client_secret:
            raise ValueError("client_secret auth requires tenant_id, client_id, and client_secret.")
        return ClientSecretCredential(
            tenant_id=auth.tenant_id,
            client_id=auth.client_id,
            client_secret=auth.client_secret,
        )

    if auth.mode == "azure_cli":
        return AzureCliCredential(tenant_id=auth.tenant_id)

    if auth.mode == "managed_identity":
        return ManagedIdentityCredential(client_id=auth.client_id)

    if auth.mode == "workload_identity":
        return DefaultAzureCredential(managed_identity_client_id=auth.client_id)

    raise ValueError(f"Unsupported Azure auth mode: {auth.mode}")

