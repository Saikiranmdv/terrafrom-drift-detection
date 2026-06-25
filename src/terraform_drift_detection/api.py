from __future__ import annotations

import json

from terraform_drift_detection.application.factory import build_scan_service
from terraform_drift_detection.config import load_config
from terraform_drift_detection.reporting.json_report import report_to_json


def create_app():
    try:
        from fastapi import FastAPI
        from fastapi import HTTPException
    except ImportError as exc:
        raise RuntimeError("Install the 'api' optional dependency to use the FastAPI app.") from exc

    app = FastAPI(title="Terraform Drift Detection", version="0.1.0")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/scan")
    def scan(config_path: str) -> dict:
        try:
            config = load_config(config_path)
            service = build_scan_service()
            report = service.run_once(config)
            return json.loads(report_to_json(report))
        except Exception as exc:  # pragma: no cover - surface scan failures over HTTP
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return app

