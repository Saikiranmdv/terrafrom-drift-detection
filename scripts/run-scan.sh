#!/usr/bin/env bash
set -euo pipefail

. .venv/bin/activate
PYTHONPATH=src terraform-drift run --config config/azure.template.yaml
