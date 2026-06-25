PYTHON ?= python3
PYCACHE_PREFIX ?= /private/tmp/terraform-drift-pycache
CONFIG ?= config/azure.template.yaml

.PHONY: bootstrap init validate doctor test scan run explain

bootstrap:
	$(PYTHON) -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -e '.[azure,dev]'

init:
	PYTHONPATH=src .venv/bin/terraform-drift init --config $(CONFIG)

validate:
	PYTHONPATH=src .venv/bin/terraform-drift validate --config $(CONFIG)

doctor:
	PYTHONPATH=src .venv/bin/terraform-drift doctor --config $(CONFIG)

test:
	PYTHONPYCACHEPREFIX=$(PYCACHE_PREFIX) $(PYTHON) -m compileall src tests
	PYTHONPATH=src:. $(PYTHON) -m unittest discover -s tests -p 'test_*.py'

scan:
	PYTHONPATH=src .venv/bin/terraform-drift scan --config $(CONFIG) --json

explain:
	PYTHONPATH=src .venv/bin/terraform-drift explain --config $(CONFIG)

run:
	PYTHONPATH=src .venv/bin/terraform-drift run --config $(CONFIG)
