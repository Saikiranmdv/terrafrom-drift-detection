#!/usr/bin/env bash
set -euo pipefail

PYTHONPYCACHEPREFIX=/private/tmp/terraform-drift-pycache python3 -m compileall src tests
PYTHONPATH=src:. python3 -m unittest discover -s tests -p 'test_*.py'

