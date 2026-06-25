from __future__ import annotations

try:
    from typing import Protocol
except ImportError:  # pragma: no cover
    from typing_extensions import Protocol

__all__ = ["Protocol"]
