from __future__ import annotations

from terraform_drift_detection.models import AiExplanation
from terraform_drift_detection.models import DriftKind
from terraform_drift_detection.models import DriftReport


def render_executive_report(report: DriftReport, verbose: bool = False, color: bool = False) -> str:
    findings_count = str(len(report.findings))
    lines = [
        _section("Summary", color=color),
        _field("scan_id", report.scan_id, color=color),
        _field("started_at", report.started_at.isoformat(), color=color),
        _field("finished_at", report.finished_at.isoformat(), color=color),
        _field("findings", _colorize_count(findings_count, len(report.findings), color=color), color=color, value_precolored=True),
    ]

    explanation = report.explanation
    if explanation is not None:
        lines.extend(_render_explanation(explanation, color=color))

    if verbose and report.findings:
        lines.append(_section("Raw Evidence Reference", color=color))
        for finding in report.findings[:20]:
            lines.append(f"  {_finding_label(finding.kind, color=color)} {finding.resource_id}")
            for change in finding.changes[:5]:
                lines.append(
                    f"    - {_dim(change.path, color=color)}: "
                    f"expected={change.expected!r} actual={change.actual!r}"
                )
    return "\n".join(lines)


def _render_explanation(explanation: AiExplanation, color: bool = False) -> list[str]:
    lines = [
        _field("ai_provider", explanation.provider, color=color),
        _field("ai_model", explanation.model, color=color),
        "",
        _section("AI Summary", color=color),
        f"  {explanation.summary}",
        "",
        _section("Key Findings", color=color),
    ]
    for item in explanation.finding_highlights or ["No high-priority findings to highlight."]:
        lines.append(f"  - {item}")
    lines.append("")
    lines.append(_section("Recent Actors", color=color))
    for item in explanation.actor_summary or ["No actor attribution available."]:
        lines.append(f"  - {item}")
    lines.append("")
    lines.append(_section("Recommended Actions", color=color))
    for item in explanation.recommended_actions or ["No recommended actions generated."]:
        lines.append(f"  - {item}")
    lines.append("")
    lines.append(_section("Limitations", color=color))
    for item in explanation.limitations or ["No limitations reported."]:
        lines.append(f"  - {_warn(item, color=color)}")
    return lines


def _field(label: str, value: str, color: bool = False, value_precolored: bool = False) -> str:
    rendered_value = value if value_precolored else str(value)
    return f"  {_label(label, color=color)}: {rendered_value}"


def _section(title: str, color: bool = False) -> str:
    return _accent(title, color=color)


def _label(value: str, color: bool = False) -> str:
    return _dim(f"{value:12}", color=color)


def _finding_label(kind: DriftKind, color: bool = False) -> str:
    label = f"[{kind.value}]"
    if not color:
        return label
    if kind == DriftKind.MISSING_IN_CLOUD:
        return _ansi(label, "31;1")
    if kind == DriftKind.CHANGED:
        return _ansi(label, "33;1")
    return _ansi(label, "36;1")


def _colorize_count(value: str, count: int, color: bool = False) -> str:
    if not color:
        return value
    if count == 0:
        return _ansi(value, "32;1")
    if count <= 3:
        return _ansi(value, "33;1")
    return _ansi(value, "31;1")


def _accent(value: str, color: bool = False) -> str:
    return _ansi(value, "36;1") if color else value


def _warn(value: str, color: bool = False) -> str:
    return _ansi(value, "33") if color else value


def _dim(value: str, color: bool = False) -> str:
    return _ansi(value, "2") if color else value


def _ansi(value: str, code: str) -> str:
    return f"\033[{code}m{value}\033[0m"
