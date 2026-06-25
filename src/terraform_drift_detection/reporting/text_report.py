from __future__ import annotations

from terraform_drift_detection.ai.service import build_fallback_explanation
from terraform_drift_detection.models import DriftReport
from terraform_drift_detection.reporting.executive import render_executive_report


def report_to_text(report: DriftReport, verbose: bool = False, color: bool = False) -> str:
    if report.explanation is None:
        report = DriftReport(
            scan_id=report.scan_id,
            started_at=report.started_at,
            finished_at=report.finished_at,
            findings=report.findings,
            explanation=build_fallback_explanation(report),
        )
    return render_executive_report(report, verbose=verbose, color=color)
