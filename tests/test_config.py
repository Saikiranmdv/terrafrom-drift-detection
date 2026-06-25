from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from terraform_drift_detection.config import load_config


class ConfigTests(unittest.TestCase):
    def test_load_config_resolves_environment_variables(self) -> None:
        previous = dict(os.environ)
        try:
            os.environ["AZURE_TENANT_ID"] = "tenant-1"
            os.environ["AZURE_SUBSCRIPTION_ID"] = "sub-1"
            os.environ["TFSTATE_STORAGE_ACCOUNT_NAME"] = "storage1"
            os.environ["TFSTATE_CONTAINER_NAME"] = "tfstate"
            os.environ["TFSTATE_BLOB_KEY"] = "dev.tfstate"

            content = """
state_sources:
  - name: primary
    type: azurerm_backend
    storage_account_name: ${TFSTATE_STORAGE_ACCOUNT_NAME}
    container_name: ${TFSTATE_CONTAINER_NAME}
    key: ${TFSTATE_BLOB_KEY}
    auth:
      mode: azure_cli
      tenant_id: ${AZURE_TENANT_ID}
scan_scope:
  subscriptions:
    - ${AZURE_SUBSCRIPTION_ID}
  include_terraform_types:
    - azurerm_resource_group
  ignored_paths: []
"""
            with tempfile.TemporaryDirectory() as temp_dir:
                path = Path(temp_dir) / "config.yaml"
                path.write_text(content, encoding="utf-8")
                config = load_config(path)
        finally:
            os.environ.clear()
            os.environ.update(previous)

        self.assertEqual("storage1", config.state_sources[0].storage_account_name)
        self.assertEqual("sub-1", config.scan_scope.subscriptions[0])


if __name__ == "__main__":
    unittest.main()
