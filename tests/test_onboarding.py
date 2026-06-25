from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from terraform_drift_detection.onboarding.service import OnboardingService
from terraform_drift_detection.onboarding.service import read_env_file


class OnboardingServiceTests(unittest.TestCase):
    def test_init_writes_env_file_from_prompts(self) -> None:
        responses = iter(
            [
                "azure_cli",
                "tenant-1",
                "sub-1",
                "storage1",
                "tfstate",
                "dev.tfstate",
                "gemini",
                "gemini-3.5-flash",
                "",
                "168",
                "",
                "",
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = str(Path(temp_dir) / ".env")
            config_path = str(Path(temp_dir) / "config.yaml")
            with patch("terraform_drift_detection.onboarding.service.input", side_effect=lambda _: next(responses, "")):
                with patch("terraform_drift_detection.onboarding.service.getpass", return_value="sk-test"):
                    result = OnboardingService().run_init(config_path=config_path, env_path=env_path)

            values = read_env_file(env_path)

        self.assertEqual("tenant-1", values["AZURE_TENANT_ID"])
        self.assertEqual("sub-1", values["AZURE_SUBSCRIPTION_ID"])
        self.assertEqual("storage1", values["TFSTATE_STORAGE_ACCOUNT_NAME"])
        self.assertTrue(result.created_config)

    def test_init_requires_confirmation_to_overwrite_existing_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("AZURE_AUTH_MODE=azure_cli\nAZURE_TENANT_ID=tenant-old\n", encoding="utf-8")
            responses = iter(
                [
                    "",
                    "tenant-new",
                    "n",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                ]
            )
            with patch("terraform_drift_detection.onboarding.service.input", side_effect=lambda _: next(responses, "")):
                with patch("terraform_drift_detection.onboarding.service.getpass", return_value=""):
                    OnboardingService().run_init(config_path=str(Path(temp_dir) / "config.yaml"), env_path=str(env_path))

            values = read_env_file(str(env_path))

        self.assertEqual("tenant-old", values["AZURE_TENANT_ID"])

    def test_init_masks_existing_secret_prompt_value(self) -> None:
        prompts: list[str] = []

        def capture_secret_prompt(prompt: str) -> str:
            prompts.append(prompt)
            return ""

        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "AZURE_AUTH_MODE=azure_cli\n"
                "AI_PROVIDER=gemini\n"
                "AI_MODEL=gemini-3.5-flash\n"
                "AI_API_KEY=sk-secret-value\n",
                encoding="utf-8",
            )
            config_path = str(Path(temp_dir) / "config.yaml")

            with patch("terraform_drift_detection.onboarding.service.input", return_value=""):
                with patch("terraform_drift_detection.onboarding.service.getpass", side_effect=capture_secret_prompt):
                    OnboardingService().run_init(config_path=config_path, env_path=str(env_path))

        self.assertIn("AI API key [configured]: ", prompts)
        self.assertNotIn("AI API key [sk-secret-value]: ", prompts)


if __name__ == "__main__":
    unittest.main()
