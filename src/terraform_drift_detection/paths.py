from __future__ import annotations

from pathlib import Path


DEFAULT_CONFIG_PATH = "config/azure.template.yaml"
DEFAULT_TEMPLATE_PATH = "config/azure.template.yaml"
DEFAULT_ENV_PATH = ".env"


def resolve_path(path: str) -> Path:
    return Path(path).expanduser().resolve()
