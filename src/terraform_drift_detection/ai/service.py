from __future__ import annotations

from dataclasses import replace
from typing import Any

from terraform_drift_detection.ai.client import AiClient
from terraform_drift_detection.models import AiExplanation
from terraform_drift_detection.models import DriftFinding
from terraform_drift_detection.models import DriftKind
from terraform_drift_detection.models import DriftReport


class ExplanationService:
    def __init__(self, ai_client: AiClient | None = None, provider_name: str = "deterministic", model: str = "rules") -> None:
        self._ai_client = ai_client
        self._provider_name = provider_name
        self._model = model

    def explain(self, report: DriftReport) -> DriftReport:
        payload = build_ai_payload(report)
        if self._ai_client is None:
            explanation = build_fallback_explanation(report, ["AI provider not configured; using deterministic summary."])
            return replace(report, explanation=explanation)

        try:
            response = self._ai_client.explain(payload)
            explanation = _coerce_explanation(
                response,
                provider_name=self._provider_name,
                model=self._model,
            )
        except Exception as exc:
            explanation = build_fallback_explanation(
                report,
                [f"AI explanation unavailable from {self._provider_name}: {exc}"],
                external_provider_attempted=True,
            )
        return replace(report, explanation=explanation)


def build_ai_payload(report: DriftReport) -> dict[str, Any]:
    findings = sorted(report.findings, key=_finding_sort_key)
    counts = {
        DriftKind.MISSING_IN_CLOUD.value: sum(1 for item in report.findings if item.kind == DriftKind.MISSING_IN_CLOUD),
        DriftKind.CHANGED.value: sum(1 for item in report.findings if item.kind == DriftKind.CHANGED),
        DriftKind.UNMANAGED_IN_CLOUD.value: sum(1 for item in report.findings if item.kind == DriftKind.UNMANAGED_IN_CLOUD),
    }
    top_findings = []
    for finding in findings[:5]:
        top_findings.append(
            {
                "kind": finding.kind.value,
                "resource_id": finding.resource_id,
                "resource_type": finding.resource_type,
                "actor": finding.changed_by,
                "timestamp": finding.changed_at,
                "operation": finding.change_operation,
                "changed_fields": [change.path for change in finding.changes[:8]],
            }
        )
    limitations = []
    if any(item.changed_by is None for item in report.findings):
        limitations.append("Some findings have no Azure Activity Log attribution.")
    return {
        "scan_id": report.scan_id,
        "started_at": report.started_at.isoformat(),
        "finished_at": report.finished_at.isoformat(),
        "counts": counts,
        "top_findings": top_findings,
        "limitations": limitations,
    }


def build_fallback_explanation(
    report: DriftReport,
    extra_limitations: list[str] | None = None,
    external_provider_attempted: bool = False,
) -> AiExplanation:
    findings = sorted(report.findings, key=_finding_sort_key)
    counts = {
        "missing_in_cloud": sum(1 for item in report.findings if item.kind == DriftKind.MISSING_IN_CLOUD),
        "changed": sum(1 for item in report.findings if item.kind == DriftKind.CHANGED),
        "unmanaged_in_cloud": sum(1 for item in report.findings if item.kind == DriftKind.UNMANAGED_IN_CLOUD),
    }
    if not report.findings:
        summary = "No drift findings were detected across the configured Azure scope."
    else:
        summary = (
            f"Detected {len(report.findings)} drift findings: "
            f"{counts['missing_in_cloud']} missing resources, "
            f"{counts['changed']} changed resources, and "
            f"{counts['unmanaged_in_cloud']} unmanaged resources."
        )

    highlights = []
    actor_summary = []
    recommended_actions = []
    for finding in findings[:5]:
        changed_fields = ", ".join(change.path for change in finding.changes[:3]) or "no field-level diff captured"
        highlights.append(f"{finding.kind.value}: {finding.resource_id} ({changed_fields})")
        if finding.changed_by or finding.change_operation or finding.changed_at:
            actor_summary.append(
                f"{finding.changed_by or 'unknown actor'} performed "
                f"{finding.change_operation or 'an unknown operation'} on "
                f"{finding.resource_id} at {finding.changed_at or 'an unknown time'}."
            )
        if finding.kind == DriftKind.MISSING_IN_CLOUD:
            recommended_actions.append(f"Verify whether {finding.resource_id} was intentionally deleted or should be recreated from Terraform.")
        elif finding.kind == DriftKind.CHANGED:
            recommended_actions.append(f"Review cloud-side changes for {finding.resource_id} and decide whether to update Terraform or revert the live resource.")
        else:
            recommended_actions.append(f"Determine whether {finding.resource_id} should be imported into Terraform or removed from Azure.")

    if external_provider_attempted:
        limitations = ["Summary generated using deterministic fallback after external AI provider failure."]
    else:
        limitations = ["Summary generated without an external AI provider."]
    if not any(item.changed_by for item in report.findings):
        limitations.append("No actor attribution was available from Azure Activity Logs.")
    if extra_limitations:
        limitations.extend(extra_limitations)
    return AiExplanation(
        provider="deterministic",
        model="rules",
        summary=summary,
        finding_highlights=_dedupe_preserve_order(highlights)[:5],
        actor_summary=_dedupe_preserve_order(actor_summary)[:5],
        recommended_actions=_dedupe_preserve_order(recommended_actions)[:5],
        limitations=_dedupe_preserve_order(limitations),
    )


def _coerce_explanation(payload: dict[str, Any], provider_name: str, model: str) -> AiExplanation:
    return AiExplanation(
        provider=provider_name,
        model=model,
        summary=str(payload.get("summary") or "").strip() or "AI summary was empty.",
        finding_highlights=_coerce_string_list(payload.get("finding_highlights")),
        actor_summary=_coerce_string_list(payload.get("actor_summary")),
        recommended_actions=_coerce_string_list(payload.get("recommended_actions")),
        limitations=_coerce_string_list(payload.get("limitations")),
    )


def _coerce_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("AI response lists must be arrays.")
    result = [str(item).strip() for item in value if str(item).strip()]
    return result


def _finding_sort_key(finding: DriftFinding) -> tuple[int, str]:
    severity = {
        DriftKind.MISSING_IN_CLOUD: 0,
        DriftKind.CHANGED: 1,
        DriftKind.UNMANAGED_IN_CLOUD: 2,
    }[finding.kind]
    return (severity, finding.resource_id)


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
