from __future__ import annotations

from datetime import datetime
from io import BytesIO
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from terraform_drift_detection.ai.client import GeminiClient
from terraform_drift_detection.ai.service import ExplanationService
from terraform_drift_detection.application.factory import build_explanation_service
from terraform_drift_detection.config import AiConfig
from terraform_drift_detection.config import AzureAuthConfig
from terraform_drift_detection.config import AzureStateSourceConfig
from terraform_drift_detection.config import ScanScopeConfig
from terraform_drift_detection.config import ScannerConfig
from terraform_drift_detection.models import DriftFinding
from terraform_drift_detection.models import DriftKind
from terraform_drift_detection.models import DriftReport


class StubAiClient:
    def __init__(self, payload: dict | Exception) -> None:
        self._payload = payload

    def explain(self, payload: dict) -> dict:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class GeminiClientTests(unittest.TestCase):
    def test_explain_parses_interactions_response(self) -> None:
        client = _StubGeminiClient(api_key="key", model="gemini-3.5-flash")

        response = client.explain({"hello": "world"})

        self.assertEqual("Gemini summary.", response["summary"])
        self.assertEqual(["Check drift."], response["recommended_actions"])

    def test_factory_builds_gemini_provider(self) -> None:
        config = ScannerConfig(
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
            ai=AiConfig(provider="gemini", model="gemini-3.5-flash", api_key="key", base_url=None),
        )

        service = build_explanation_service(config)

        self.assertIsInstance(service, ExplanationService)

    def test_gemini_retries_transient_503_and_succeeds(self) -> None:
        client = GeminiClient(
            api_key="key",
            model="gemini-3.5-flash",
            max_attempts=3,
            retry_delay_seconds=0,
        )
        response = _JsonResponse(
            b'{"id":"abc","object":"interaction","status":"completed","steps":[{"type":"model_output","content":[{"type":"text","text":"{\\"summary\\":\\"Recovered summary.\\",\\"finding_highlights\\":[],\\"actor_summary\\":[],\\"recommended_actions\\":[],\\"limitations\\":[]}"}]}]}'
        )
        service_unavailable = HTTPError(
            url="https://example.test",
            code=503,
            msg="Service Unavailable",
            hdrs=None,
            fp=BytesIO(b""),
        )

        with patch("terraform_drift_detection.ai.client.request.urlopen", side_effect=[service_unavailable, response]) as urlopen:
            with patch("terraform_drift_detection.ai.client.time.sleep") as sleep:
                payload = client.explain({"hello": "world"})

        self.assertEqual("Recovered summary.", payload["summary"])
        self.assertEqual(2, urlopen.call_count)
        sleep.assert_called_once()

    def test_gemini_surfaces_http_error_details(self) -> None:
        client = GeminiClient(
            api_key="key",
            model="gemini-3.5-flash",
            max_attempts=1,
            retry_delay_seconds=0,
        )
        service_unavailable = HTTPError(
            url="https://example.test",
            code=503,
            msg="Service Unavailable",
            hdrs=None,
            fp=BytesIO(b'{"error":{"status":"UNAVAILABLE","message":"backend overloaded"}}'),
        )

        with patch("terraform_drift_detection.ai.client.request.urlopen", side_effect=service_unavailable):
            with self.assertRaises(RuntimeError) as raised:
                client.explain({"hello": "world"})

        self.assertIn("HTTP 503 Service Unavailable", str(raised.exception))
        self.assertIn("UNAVAILABLE - backend overloaded", str(raised.exception))


class ExplanationServiceTests(unittest.TestCase):
    def test_fallback_summary_when_ai_not_configured(self) -> None:
        report = _sample_report()

        explained = ExplanationService().explain(report)

        self.assertIsNotNone(explained.explanation)
        assert explained.explanation is not None
        self.assertEqual("deterministic", explained.explanation.provider)
        self.assertIn("Detected 1 drift findings", explained.explanation.summary)

    def test_ai_summary_when_client_returns_valid_payload(self) -> None:
        report = _sample_report()
        client = StubAiClient(
            {
                "summary": "One high-priority drift requires review.",
                "finding_highlights": ["Resource group tags changed."],
                "actor_summary": ["alice@example.com changed the resource group."],
                "recommended_actions": ["Review the manual tag update."],
                "limitations": ["Actor data may be incomplete."],
            }
        )

        explained = ExplanationService(client, provider_name="openai_compatible", model="gpt-test").explain(report)

        assert explained.explanation is not None
        self.assertEqual("openai_compatible", explained.explanation.provider)
        self.assertEqual("gpt-test", explained.explanation.model)
        self.assertEqual("One high-priority drift requires review.", explained.explanation.summary)

    def test_malformed_ai_response_falls_back(self) -> None:
        report = _sample_report()
        client = StubAiClient({"summary": "bad", "finding_highlights": "not-a-list"})

        explained = ExplanationService(client, provider_name="openai_compatible", model="gpt-test").explain(report)

        assert explained.explanation is not None
        self.assertEqual("deterministic", explained.explanation.provider)
        self.assertIn(
            "Summary generated using deterministic fallback after external AI provider failure.",
            explained.explanation.limitations,
        )
        self.assertTrue(any("AI explanation unavailable from openai_compatible" in item for item in explained.explanation.limitations))


def _sample_report() -> DriftReport:
    return DriftReport(
        scan_id="scan-1",
        started_at=datetime(2026, 1, 1, 0, 0, 0),
        finished_at=datetime(2026, 1, 1, 0, 1, 0),
        findings=[
            DriftFinding(
                kind=DriftKind.CHANGED,
                resource_id="/subscriptions/sub-1/resourceGroups/rg-1",
                resource_type="microsoft.resources/subscriptions/resourcegroups",
                address="azurerm_resource_group.rg[0]",
                changes=[],
                changed_by="alice@example.com",
                changed_at="2026-01-01T00:00:00",
                change_operation="Microsoft.Resources/subscriptions/resourceGroups/write",
            )
        ],
    )


class _StubGeminiClient(GeminiClient):
    def _post_json(self, payload: dict) -> dict:
        return {
            "id": "test-interaction",
            "object": "interaction",
            "status": "completed",
            "steps": [
                {
                    "type": "model_output",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                '{"summary":"Gemini summary.",'
                                '"finding_highlights":["Changed tag."],'
                                '"actor_summary":["alice@example.com updated the resource."],'
                                '"recommended_actions":["Check drift."],'
                                '"limitations":["Actor data may be partial."]}'
                            ),
                        }
                    ],
                }
            ],
        }


class _JsonResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> "_JsonResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


if __name__ == "__main__":
    unittest.main()
