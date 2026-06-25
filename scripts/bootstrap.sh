#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -e '.[azure,dev]'

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

echo "Bootstrap complete."
echo "Next:"
echo "  1. Run: ./.venv/bin/terraform-drift init"
echo "  2. Run: ./scripts/validate.sh"
echo "  3. Run: ./scripts/run-scan.sh"
