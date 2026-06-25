from __future__ import annotations

import json

from terraform_drift_detection.models import DriftReport


def report_to_json(report: DriftReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True)

