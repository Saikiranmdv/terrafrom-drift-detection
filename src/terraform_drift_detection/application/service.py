from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from terraform_drift_detection.application.contracts import ActualInventorySource
from terraform_drift_detection.application.contracts import ExpectedStateSource
from terraform_drift_detection.config import ScannerConfig
from terraform_drift_detection.models import DriftReport
from terraform_drift_detection.models import ResourceSnapshot


class DriftScanService:
    def __init__(
        self,
        state_source: ExpectedStateSource,
        actual_inventory: ActualInventorySource,
        diff_engine,
        drift_attributor=None,
    ) -> None:
        self._state_source = state_source
        self._actual_inventory = actual_inventory
        self._diff_engine = diff_engine
        self._drift_attributor = drift_attributor

    def run_once(self, config: ScannerConfig) -> DriftReport:
        started_at = datetime.utcnow()
        expected_resources = self._load_expected_resources(config)
        actual_resources = self._actual_inventory.load_actual_resources(
            expected_resources=expected_resources,
            subscriptions=config.scan_scope.subscriptions,
            auth=config.state_sources[0].auth,
        )
        findings = self._diff_engine.compare(
            expected=expected_resources,
            actual=actual_resources,
            ignored_paths=config.scan_scope.ignored_paths,
        )
        if self._drift_attributor:
            findings = self._drift_attributor.enrich(
                findings=findings,
                subscriptions=config.scan_scope.subscriptions,
                lookback_hours=config.scan_scope.activity_log_lookback_hours,
                auth=config.state_sources[0].auth,
            )
        finished_at = datetime.utcnow()
        return DriftReport(
            scan_id=str(uuid4()),
            started_at=started_at,
            finished_at=finished_at,
            findings=findings,
        )

    def _load_expected_resources(self, config: ScannerConfig) -> list[ResourceSnapshot]:
        include_types = set(config.scan_scope.include_terraform_types)
        expected_resources: list[ResourceSnapshot] = []
        for state_source in config.state_sources:
            resources = self._state_source.load_expected_resources(state_source)
            if include_types:
                resources = [item for item in resources if item.terraform_type in include_types]
            expected_resources.extend(resources)
        return expected_resources
