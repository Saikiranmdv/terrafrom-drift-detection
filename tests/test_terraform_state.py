from __future__ import annotations

import json
from pathlib import Path
import unittest

from terraform_drift_detection.state.terraform_state import TerraformStateParser


class TerraformStateParserTests(unittest.TestCase):
    def test_parse_document_extracts_supported_azure_resources(self) -> None:
        fixture_path = Path(__file__).parent / "fixtures" / "sample.tfstate.json"
        document = json.loads(fixture_path.read_text(encoding="utf-8"))

        snapshots = TerraformStateParser().parse_document(document)

        self.assertEqual(2, len(snapshots))
        self.assertEqual("azurerm_resource_group", snapshots[0].terraform_type)
        self.assertEqual("rg-prod", snapshots[0].resource_group)
        self.assertEqual(["10.0.0.0/16"], snapshots[1].attributes["address_space"])


if __name__ == "__main__":
    unittest.main()
