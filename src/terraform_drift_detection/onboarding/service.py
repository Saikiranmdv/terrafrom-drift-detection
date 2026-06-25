from __future__ import annotations

from dataclasses import dataclass
from getpass import getpass
from pathlib import Path
import shutil

from terraform_drift_detection.paths import DEFAULT_ENV_PATH
from terraform_drift_detection.paths import DEFAULT_TEMPLATE_PATH


PROMPT_ORDER = [
    ("AZURE_AUTH_MODE", "Azure auth mode", "azure_cli", False),
    ("AZURE_TENANT_ID", "Azure tenant ID", "", False),
    ("AZURE_SUBSCRIPTION_ID", "Azure subscription ID", "", False),
    ("TFSTATE_STORAGE_ACCOUNT_NAME", "Terraform state storage account name", "", False),
    ("TFSTATE_CONTAINER_NAME", "Terraform state container name", "tfstate", False),
    ("TFSTATE_BLOB_KEY", "Terraform state blob key", "", False),
    ("AI_PROVIDER", "AI provider", "gemini", False),
    ("AI_MODEL", "AI model", "gemini-3.5-flash", False),
    ("AI_API_KEY", "AI API key", "", True),
    ("AI_BASE_URL", "AI base URL", "", False),
    ("ACTIVITY_LOG_LOOKBACK_HOURS", "Activity log lookback hours", "168", False),
]


@dataclass(frozen=True)
class InitResult:
    env_path: str
    config_path: str
    created_config: bool


class OnboardingService:
    def run_init(self, config_path: str, env_path: str = DEFAULT_ENV_PATH) -> InitResult:
        existing = read_env_file(env_path)
        updated = dict(existing)
        auth_mode = _prompt_value("AZURE_AUTH_MODE", "Azure auth mode", existing.get("AZURE_AUTH_MODE", "azure_cli"), False)
        updated["AZURE_AUTH_MODE"] = auth_mode

        for key, label, default, secret in PROMPT_ORDER[1:]:
            if key in {"AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET"}:
                continue
            if key in {"AI_PROVIDER", "AI_MODEL", "AI_API_KEY", "AI_BASE_URL"} and updated.get("AI_PROVIDER", "openai_compatible").strip() == "":
                continue
            value_default = existing.get(key, default)
            updated[key] = _prompt_value(key, label, value_default, secret)

        if auth_mode in {"client_secret", "workload_identity", "managed_identity"}:
            updated["AZURE_CLIENT_ID"] = _prompt_value(
                "AZURE_CLIENT_ID",
                "Azure client ID",
                existing.get("AZURE_CLIENT_ID", ""),
                False,
            )
        if auth_mode == "client_secret":
            updated["AZURE_CLIENT_SECRET"] = _prompt_value(
                "AZURE_CLIENT_SECRET",
                "Azure client secret",
                existing.get("AZURE_CLIENT_SECRET", ""),
                True,
            )

        write_env_file(env_path, updated)

        created_config = False
        config_file = Path(config_path)
        if not config_file.exists():
            template_path = Path(DEFAULT_TEMPLATE_PATH)
            if config_file != template_path and template_path.exists():
                config_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(template_path, config_file)
                created_config = True
        return InitResult(env_path=env_path, config_path=config_path, created_config=created_config)


def read_env_file(path: str) -> dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        return {}
    result: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip("'").strip('"')
    return result


def write_env_file(path: str, values: dict[str, str]) -> None:
    lines = [f"{key}={_quote_env_value(value)}" for key, value in sorted(values.items()) if value is not None]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _quote_env_value(value: str) -> str:
    if value == "":
        return ""
    if any(character.isspace() for character in value):
        return f'"{value}"'
    return value


def _prompt_value(key: str, label: str, current: str, secret: bool) -> str:
    if secret:
        default_hint = " [configured]" if current else ""
    else:
        default_hint = f" [{current}]" if current else ""
    prompt = f"{label}{default_hint}: "
    entered = getpass(prompt) if secret else input(prompt)
    entered = entered.strip()
    if not entered:
        return current
    if current and entered != current:
        confirmation = input(f"Overwrite existing value for {key}? [y/N]: ").strip().lower()
        if confirmation not in {"y", "yes"}:
            return current
    return entered
