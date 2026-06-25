from __future__ import annotations

from datetime import datetime
import io
import unittest
from unittest.mock import patch

from terraform_drift_detection import cli
from terraform_drift_detection.diagnostics.service import DiagnosticCheck
from terraform_drift_detection.diagnostics.service import DiagnosticReport
from terraform_drift_detection.models import AiExplanation
from terraform_drift_detection.models import DriftReport


class CliRunTests(unittest.TestCase):
    def test_run_happy_path_prints_executive_summary(self) -> None:
        config = object()
        scan_report = DriftReport(
            scan_id="scan-1",
            started_at=datetime(2026, 1, 1, 0, 0, 0),
            finished_at=datetime(2026, 1, 1, 0, 1, 0),
            findings=[],
        )
        explained_report = DriftReport(
            scan_id="scan-1",
            started_at=scan_report.started_at,
            finished_at=scan_report.finished_at,
            findings=[],
            explanation=AiExplanation(
                provider="deterministic",
                model="rules",
                summary="No drift findings were detected across the configured Azure scope.",
                finding_highlights=[],
                actor_summary=[],
                recommended_actions=[],
                limitations=[],
            ),
        )

        stdout = io.StringIO()
        with patch("sys.argv", ["terraform-drift", "run", "--config", "config/azure.template.yaml"]):
            with patch("sys.stdout", stdout):
                with patch("terraform_drift_detection.cli.validate_config", return_value=config):
                    with patch("terraform_drift_detection.cli.AzureDiagnosticsRunner") as runner_cls:
                        runner_cls.return_value.validate.return_value = DiagnosticReport(
                            checks=[DiagnosticCheck(name="azure_auth", ok=True, detail="ok")]
                        )
                        with patch("terraform_drift_detection.cli.build_scan_service") as scan_factory:
                            scan_factory.return_value.run_once.return_value = scan_report
                            with patch("terraform_drift_detection.cli.build_explanation_service") as explain_factory:
                                explain_factory.return_value.explain.return_value = explained_report
                                exit_code = cli.main()

        self.assertEqual(0, exit_code)
        output = stdout.getvalue()
        self.assertIn("doctor_status=ok", output)
        self.assertIn("No drift findings were detected", output)

    def test_run_no_color_flag_disables_ansi_output(self) -> None:
        config = object()
        scan_report = DriftReport(
            scan_id="scan-1",
            started_at=datetime(2026, 1, 1, 0, 0, 0),
            finished_at=datetime(2026, 1, 1, 0, 1, 0),
            findings=[],
        )
        explained_report = DriftReport(
            scan_id="scan-1",
            started_at=scan_report.started_at,
            finished_at=scan_report.finished_at,
            findings=[],
            explanation=AiExplanation(
                provider="deterministic",
                model="rules",
                summary="No drift findings were detected across the configured Azure scope.",
                finding_highlights=[],
                actor_summary=[],
                recommended_actions=[],
                limitations=[],
            ),
        )

        class _TtyStringIO(io.StringIO):
            def isatty(self) -> bool:
                return True

        stdout = _TtyStringIO()
        with patch("sys.argv", ["terraform-drift", "run", "--config", "config/azure.template.yaml", "--no-color"]):
            with patch("sys.stdout", stdout):
                with patch("terraform_drift_detection.cli.validate_config", return_value=config):
                    with patch("terraform_drift_detection.cli.AzureDiagnosticsRunner") as runner_cls:
                        runner_cls.return_value.validate.return_value = DiagnosticReport(
                            checks=[DiagnosticCheck(name="azure_auth", ok=True, detail="ok")]
                        )
                        with patch("terraform_drift_detection.cli.build_scan_service") as scan_factory:
                            scan_factory.return_value.run_once.return_value = scan_report
                            with patch("terraform_drift_detection.cli.build_explanation_service") as explain_factory:
                                explain_factory.return_value.explain.return_value = explained_report
                                exit_code = cli.main()

        self.assertEqual(0, exit_code)
        self.assertNotIn("\033[", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
