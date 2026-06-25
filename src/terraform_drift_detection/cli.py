from __future__ import annotations

import argparse
import json
import os
import sys

from terraform_drift_detection.application.factory import build_explanation_service
from terraform_drift_detection.application.factory import build_scan_service
from terraform_drift_detection.config import load_config
from terraform_drift_detection.config import validate_config
from terraform_drift_detection.diagnostics.service import AzureDiagnosticsRunner
from terraform_drift_detection.onboarding.service import OnboardingService
from terraform_drift_detection.paths import DEFAULT_CONFIG_PATH
from terraform_drift_detection.reporting.json_report import report_to_json
from terraform_drift_detection.reporting.parse_report import report_from_dict
from terraform_drift_detection.reporting.text_report import report_to_text


def main() -> int:
    parser = argparse.ArgumentParser(prog="terraform-drift")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Run a drift scan")
    scan_parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to scanner YAML config")
    scan_parser.add_argument("--json", action="store_true", help="Emit the full report as JSON")
    scan_parser.add_argument("--verbose", action="store_true", help="Emit verbose text output")
    scan_parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors in text output")

    validate_parser = subparsers.add_parser("validate", help="Validate config and local prerequisites")
    validate_parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to scanner YAML config")
    validate_parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors in text output")

    init_parser = subparsers.add_parser("init", help="Collect Azure and AI details and persist them locally")
    init_parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to scanner YAML config")
    init_parser.add_argument("--env-file", default=".env", help="Path to the env file to write")

    doctor_parser = subparsers.add_parser("doctor", help="Run Azure prerequisite checks")
    doctor_parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to scanner YAML config")
    doctor_parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors in text output")

    explain_parser = subparsers.add_parser("explain", help="Generate an executive AI summary")
    explain_parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to scanner YAML config")
    explain_parser.add_argument("--input-report", help="Path to an existing JSON drift report")
    explain_parser.add_argument("--json", action="store_true", help="Emit the explained report as JSON")
    explain_parser.add_argument("--verbose", action="store_true", help="Emit verbose text output")
    explain_parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors in text output")

    run_parser = subparsers.add_parser("run", help="Validate, scan, and explain in one command")
    run_parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to scanner YAML config")
    run_parser.add_argument("--json", action="store_true", help="Emit the explained report as JSON")
    run_parser.add_argument("--verbose", action="store_true", help="Emit verbose text output")
    run_parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors in text output")

    args = parser.parse_args()
    color = _should_use_color(args)

    if args.command == "scan":
        config = load_config(args.config)
        report = build_scan_service().run_once(config)
        return _emit_report(report, emit_json=args.json, verbose=args.verbose, color=color)

    if args.command == "validate":
        config = validate_config(args.config)
        _print_validation_summary(config, color=color)
        return 0

    if args.command == "init":
        result = OnboardingService().run_init(config_path=args.config, env_path=args.env_file)
        print(f"env_file={result.env_path}")
        print(f"config_file={result.config_path}")
        print(f"created_config={str(result.created_config).lower()}")
        return 0

    if args.command == "doctor":
        config = validate_config(args.config)
        diagnostic_report = AzureDiagnosticsRunner().validate(config)
        print(_format_diagnostic_report(diagnostic_report, color=color))
        return 0 if diagnostic_report.ok else 1

    if args.command == "explain":
        config = load_config(args.config)
        report = _load_or_create_report(config, args.input_report)
        explained_report = build_explanation_service(config).explain(report)
        return _emit_report(explained_report, emit_json=args.json, verbose=args.verbose, color=color)

    if args.command == "run":
        config = validate_config(args.config)
        diagnostic_report = AzureDiagnosticsRunner().validate(config)
        print(_format_diagnostic_report(diagnostic_report, color=color))
        if not diagnostic_report.ok:
            return 1
        report = build_scan_service().run_once(config)
        explained_report = build_explanation_service(config).explain(report)
        return _emit_report(explained_report, emit_json=args.json, verbose=args.verbose, color=color)

    parser.print_help()
    return 1


def _emit_report(report: object, emit_json: bool, verbose: bool, color: bool) -> int:
    if emit_json:
        print(report_to_json(report))
    else:
        print(report_to_text(report, verbose=verbose, color=color))
    return 0


def _print_validation_summary(config: object, color: bool = False) -> None:
    from terraform_drift_detection.config import ScannerConfig

    if not isinstance(config, ScannerConfig):
        raise TypeError("Expected a ScannerConfig.")

    status = _ansi("ok", "32;1") if color else "ok"
    print(f"config={status}")
    print(f"state_sources={len(config.state_sources)}")
    print(f"subscriptions={len(config.scan_scope.subscriptions)}")
    print(f"ai_provider={config.ai.provider or 'disabled'}")
    for source in config.state_sources:
        print(
            f"state_source name={source.name} "
            f"account={source.storage_account_name} "
            f"container={source.container_name} "
            f"key={source.key} "
            f"auth_mode={source.auth.mode}"
        )


def _format_diagnostic_report(report: object, color: bool = False) -> str:
    from terraform_drift_detection.diagnostics.service import DiagnosticReport

    if not isinstance(report, DiagnosticReport):
        raise TypeError("Expected a DiagnosticReport.")

    status = "ok" if report.ok else "failed"
    if color:
        status = _ansi(status, "32;1" if report.ok else "31;1")
    lines = [f"doctor_status={status}"]
    for check in report.checks:
        marker = "PASS" if check.ok else "FAIL"
        if color:
            marker = _ansi(marker, "32;1" if check.ok else "31;1")
        lines.append(f"[{marker}] {check.name}: {check.detail}")
    return "\n".join(lines)


def _should_use_color(args: argparse.Namespace) -> bool:
    if getattr(args, "json", False):
        return False
    if getattr(args, "no_color", False):
        return False
    if os.environ.get("NO_COLOR") is not None:
        return False
    isatty = getattr(sys.stdout, "isatty", None)
    return bool(callable(isatty) and isatty())


def _ansi(value: str, code: str) -> str:
    return f"\033[{code}m{value}\033[0m"


def _load_or_create_report(config: object, input_report: str | None):
    if input_report:
        with open(input_report, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return report_from_dict(payload)
    return build_scan_service().run_once(config)


if __name__ == "__main__":
    sys.exit(main())
