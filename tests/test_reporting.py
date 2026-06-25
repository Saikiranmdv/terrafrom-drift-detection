from __future__ import annotations

from datetime import datetime
import unittest

from terraform_drift_detection.models import AiExplanation
from terraform_drift_detection.models import DriftFinding
from terraform_drift_detection.models import DriftKind
from terraform_drift_detection.models import DriftReport
from terraform_drift_detection.models import FieldChange
from terraform_drift_detection.reporting.text_report import report_to_text


class ReportingTests(unittest.TestCase):
    def test_report_to_text_renders_executive_and_verbose_sections(self) -> None:
        report = DriftReport(
            scan_id="scan-1",
            started_at=datetime(2026, 1, 1, 0, 0, 0),
            finished_at=datetime(2026, 1, 1, 0, 1, 0),
            findings=[
                DriftFinding(
                    kind=DriftKind.CHANGED,
                    resource_id="/subscriptions/sub-1/resourceGroups/rg-1",
                    resource_type="microsoft.resources/subscriptions/resourcegroups",
                    address="azurerm_resource_group.rg[0]",
                    changes=[FieldChange(path="tags.env", expected="prod", actual="dev")],
                )
            ],
            explanation=AiExplanation(
                provider="openai_compatible",
                model="gpt-test",
                summary="One change detected.",
                finding_highlights=["Resource group tags changed."],
                actor_summary=["No actor data available."],
                recommended_actions=["Review the tag change."],
                limitations=["Activity Log data was incomplete."],
            ),
        )

        output = report_to_text(report, verbose=True)

        self.assertIn("Summary", output)
        self.assertIn("Key Findings", output)
        self.assertIn("Raw Evidence Reference", output)
        self.assertIn("tags.env", output)

    def test_report_to_text_can_render_with_ansi_colors(self) -> None:
        report = DriftReport(
            scan_id="scan-1",
            started_at=datetime(2026, 1, 1, 0, 0, 0),
            finished_at=datetime(2026, 1, 1, 0, 1, 0),
            findings=[],
            explanation=AiExplanation(
                provider="gemini",
                model="gemini-2.5-flash",
                summary="No changes detected.",
                finding_highlights=[],
                actor_summary=[],
                recommended_actions=[],
                limitations=[],
            ),
        )

        output = report_to_text(report, color=True)

        self.assertIn("\033[", output)
        self.assertIn("AI Summary", output)


if __name__ == "__main__":
    unittest.main()
