from __future__ import annotations

from terraform_drift_detection.ai.client import GeminiClient
from terraform_drift_detection.ai.client import OpenAiCompatibleClient
from terraform_drift_detection.ai.service import ExplanationService
from terraform_drift_detection.application.service import DriftScanService
from terraform_drift_detection.config import ScannerConfig
from terraform_drift_detection.diff import DriftEngine
from terraform_drift_detection.providers.azure.activity_logs import AzureActivityLogAttributor
from terraform_drift_detection.providers.azure.resource_graph import AzureResourceGraphInventory
from terraform_drift_detection.state.azure_blob_backend import AzureBlobStateSource
from terraform_drift_detection.state.terraform_state import TerraformStateParser


def build_scan_service() -> DriftScanService:
    parser = TerraformStateParser()
    state_source = AzureBlobStateSource(parser=parser)
    inventory = AzureResourceGraphInventory()
    attributor = AzureActivityLogAttributor()
    return DriftScanService(
        state_source=state_source,
        actual_inventory=inventory,
        diff_engine=DriftEngine(),
        drift_attributor=attributor,
    )


def build_explanation_service(config: ScannerConfig) -> ExplanationService:
    if config.ai.provider == "openai_compatible" and config.ai.api_key and config.ai.model:
        client = OpenAiCompatibleClient(
            api_key=config.ai.api_key,
            model=config.ai.model,
            base_url=config.ai.base_url or "https://api.openai.com/v1/chat/completions",
            provider_name=config.ai.provider,
        )
        return ExplanationService(
            ai_client=client,
            provider_name=config.ai.provider,
            model=config.ai.model,
        )
    if config.ai.provider == "gemini" and config.ai.api_key and config.ai.model:
        client = GeminiClient(
            api_key=config.ai.api_key,
            model=config.ai.model,
            base_url=config.ai.base_url,
            provider_name=config.ai.provider,
        )
        return ExplanationService(
            ai_client=client,
            provider_name=config.ai.provider,
            model=config.ai.model,
        )
    return ExplanationService()
