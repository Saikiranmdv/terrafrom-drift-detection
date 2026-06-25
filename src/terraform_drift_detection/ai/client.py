from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import HTTPError
from urllib import request

from terraform_drift_detection.compat import Protocol


class AiClient(Protocol):
    def explain(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...


class OpenAiCompatibleClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1/chat/completions",
        provider_name: str = "openai_compatible",
        timeout_seconds: int = 30,
        max_attempts: int = 3,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._provider_name = provider_name
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model(self) -> str:
        return self._model

    def explain(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = {
            "model": self._model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": json.dumps(payload, sort_keys=True)},
            ],
        }
        raw_response = self._post_json(body)
        content = self._extract_content(raw_response)
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("AI response must be a JSON object.")
        return parsed

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self._base_url,
            data=encoded,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        return self._execute_with_retry(req)

    def _execute_with_retry(self, req: request.Request) -> dict[str, Any]:
        for attempt in range(1, self._max_attempts + 1):
            try:
                with request.urlopen(req, timeout=self._timeout_seconds) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                if attempt == self._max_attempts or exc.code not in _RETRYABLE_HTTP_STATUS_CODES:
                    raise RuntimeError(_format_http_error(exc)) from exc
                time.sleep(self._retry_delay_seconds * attempt)
        raise RuntimeError("Exhausted AI request retries.")

    def _extract_content(self, response_payload: dict[str, Any]) -> str:
        choices = response_payload.get("choices") or []
        if not choices:
            raise ValueError("AI response did not contain choices.")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [item.get("text", "") for item in content if isinstance(item, dict)]
            joined = "".join(parts).strip()
            if joined:
                return joined
        raise ValueError("AI response did not contain message content.")


def _system_prompt() -> str:
    return (
        "You are an expert infrastructure drift analysis assistant specializing in Terraform state management. "
        "Your role is to analyze infrastructure changes and provide detailed, actionable insights. "
        "Always respond with valid JSON only—no additional text or markdown formatting. "
        "\n"
        "Analyze the provided infrastructure drift data and return a JSON object with these exact keys:\n"
        "- 'summary': A comprehensive 2-3 sentence overview of the detected drift, its severity, and business impact.\n"
        "- 'finding_highlights': An array of specific, concrete findings. Each item should be a single clear observation about what changed, why it matters, and any potential risks.\n"
        "- 'actor_summary': An array describing who or what likely caused each change (e.g., manual intervention, automation, external service, etc.).\n"
        "- 'recommended_actions': An array of prioritized, specific remediation steps. Include commands or procedures where applicable.\n"
        "- 'limitations': An array of caveats, assumptions, or gaps in your analysis. Be honest about what you cannot determine from the data.\n"
        "\n"
        "Guidelines:\n"
        "1. All array items must be concise strings (2-4 sentences maximum).\n"
        "2. Do not invent or speculate about missing data—explicitly note gaps in 'limitations'.\n"
        "3. Prioritize findings by severity and business impact.\n"
        "4. Be specific: reference resource names, property changes, and timestamps where available.\n"
        "5. Maintain a professional, neutral tone.\n"
        "6. Ensure the JSON is valid and parseable."
    )


class GeminiClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        provider_name: str = "gemini",
        timeout_seconds: int = 30,
        max_attempts: int = 3,
        retry_delay_seconds: float = 1.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = (
            base_url
            or "https://generativelanguage.googleapis.com/v1beta/interactions"
        )
        self._provider_name = provider_name
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def model(self) -> str:
        return self._model

    def explain(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = {
            "model": self._model,
            "system_instruction": _system_prompt(),
            "input": json.dumps(payload, sort_keys=True),
            "store": False,
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": _explanation_schema(),
            },
            "generation_config": {
                "temperature": 0,
            },
        }
        raw_response = self._post_json(body)
        content = self._extract_content(raw_response)
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("AI response must be a JSON object.")
        return parsed

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        encoded = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self._base_url,
            data=encoded,
            headers={
                "x-goog-api-key": self._api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        return self._execute_with_retry(req)

    def _execute_with_retry(self, req: request.Request) -> dict[str, Any]:
        for attempt in range(1, self._max_attempts + 1):
            try:
                with request.urlopen(req, timeout=self._timeout_seconds) as response:
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                if attempt == self._max_attempts or exc.code not in _RETRYABLE_HTTP_STATUS_CODES:
                    raise RuntimeError(_format_http_error(exc)) from exc
                time.sleep(self._retry_delay_seconds * attempt)
        raise RuntimeError("Exhausted AI request retries.")

    def _extract_content(self, response_payload: dict[str, Any]) -> str:
        output_text = response_payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        steps = response_payload.get("steps") or []
        texts: list[str] = []
        for step in steps:
            if not isinstance(step, dict) or step.get("type") != "model_output":
                continue
            for content in step.get("content") or []:
                if isinstance(content, dict) and content.get("type") == "text":
                    text = str(content.get("text") or "").strip()
                    if text:
                        texts.append(text)
        joined = "".join(texts).strip()
        if not joined:
            raise ValueError("Gemini interaction response did not contain text output.")
        return joined


def _explanation_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "finding_highlights": {
                "type": "array",
                "items": {"type": "string"},
            },
            "actor_summary": {
                "type": "array",
                "items": {"type": "string"},
            },
            "recommended_actions": {
                "type": "array",
                "items": {"type": "string"},
            },
            "limitations": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "summary",
            "finding_highlights",
            "actor_summary",
            "recommended_actions",
            "limitations",
        ],
    }


_RETRYABLE_HTTP_STATUS_CODES = {429, 500, 502, 503, 504}


def _format_http_error(exc: HTTPError) -> str:
    detail = ""
    if exc.fp is not None:
        try:
            body = exc.fp.read().decode("utf-8", errors="replace").strip()
        except Exception:
            body = ""
        if body:
            detail = _summarize_error_body(body)
    message = f"HTTP {exc.code} {exc.reason}"
    if detail:
        return f"{message}: {detail}"
    return message


def _summarize_error_body(body: str) -> str:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return body[:400]

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            status = error.get("status")
            parts = [str(item).strip() for item in [status, message] if str(item).strip()]
            if parts:
                return " - ".join(parts)
        message = payload.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    return body[:400]
