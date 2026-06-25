from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Any


@dataclass(frozen=True)
class AzureAuthConfig:
    mode: str
    tenant_id: str | None = None
    client_id: str | None = None
    client_secret: str | None = None


@dataclass(frozen=True)
class AzureStateSourceConfig:
    name: str
    type: str
    storage_account_name: str
    container_name: str
    key: str
    auth: AzureAuthConfig


@dataclass(frozen=True)
class AiConfig:
    provider: str | None = None
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None


@dataclass(frozen=True)
class ScanScopeConfig:
    subscriptions: list[str]
    include_terraform_types: list[str]
    ignored_paths: list[str]
    activity_log_lookback_hours: int = 168


@dataclass(frozen=True)
class ScannerConfig:
    state_sources: list[AzureStateSourceConfig]
    scan_scope: ScanScopeConfig
    ai: AiConfig


def load_config(path: str | Path) -> ScannerConfig:
    _load_dotenv()
    document = _read_yaml(path)
    document = _resolve_env_vars(document)
    state_sources = [
        AzureStateSourceConfig(
            name=item["name"],
            type=item["type"],
            storage_account_name=item["storage_account_name"],
            container_name=item["container_name"],
            key=item["key"],
            auth=AzureAuthConfig(**item["auth"]),
        )
        for item in document["state_sources"]
    ]
    scan_scope_doc = document["scan_scope"]
    scan_scope = ScanScopeConfig(
        subscriptions=list(scan_scope_doc.get("subscriptions", [])),
        include_terraform_types=list(scan_scope_doc.get("include_terraform_types", [])),
        ignored_paths=list(scan_scope_doc.get("ignored_paths", [])),
        activity_log_lookback_hours=int(scan_scope_doc.get("activity_log_lookback_hours", 168)),
    )
    ai = AiConfig(
        provider=_none_if_blank(os.environ.get("AI_PROVIDER")),
        model=_none_if_blank(os.environ.get("AI_MODEL")),
        api_key=_none_if_blank(os.environ.get("AI_API_KEY")),
        base_url=_none_if_blank(os.environ.get("AI_BASE_URL")),
    )
    return ScannerConfig(state_sources=state_sources, scan_scope=scan_scope, ai=ai)


def _read_yaml(path: str | Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to load scanner configuration.") from exc

    with Path(path).open("r", encoding="utf-8") as handle:
        document = yaml.safe_load(handle)

    if not isinstance(document, dict):
        raise ValueError("Configuration root must be a mapping.")
    return document


def validate_config(path: str | Path) -> ScannerConfig:
    config = load_config(path)
    if not config.state_sources:
        raise ValueError("At least one state source is required.")
    if not config.scan_scope.subscriptions:
        raise ValueError("At least one subscription is required.")
    for source in config.state_sources:
        if source.type != "azurerm_backend":
            raise ValueError(f"Unsupported state source type: {source.type}")
        if not source.storage_account_name:
            raise ValueError("storage_account_name is required.")
        if not source.container_name:
            raise ValueError("container_name is required.")
        if not source.key:
            raise ValueError("key is required.")
        if source.auth.mode not in {"azure_cli", "client_secret", "managed_identity", "workload_identity"}:
            raise ValueError(f"Unsupported Azure auth mode: {source.auth.mode}")
        if source.auth.mode == "client_secret":
            if not source.auth.tenant_id or not source.auth.client_id or not source.auth.client_secret:
                raise ValueError("client_secret auth requires tenant_id, client_id, and client_secret.")
    return config


def _load_dotenv(path: str | Path = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def _resolve_env_vars(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _resolve_env_vars(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    if isinstance(value, str):
        return _resolve_env_string(value)
    return value


def _resolve_env_string(value: str) -> str:
    pattern = re.compile(r"\$\{([A-Z0-9_]+)(?::-([^}]*))?\}")

    def replacer(match: re.Match[str]) -> str:
        variable_name = match.group(1)
        default_value = match.group(2)
        resolved = os.environ.get(variable_name, default_value)
        if resolved is None:
            raise ValueError(f"Missing required environment variable: {variable_name}")
        return resolved

    return pattern.sub(replacer, value)


def _none_if_blank(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
