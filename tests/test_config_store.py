from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys


SCRIPTS_PATH = Path(__file__).resolve().parents[1] / "plugins" / "climate" / "scripts"
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

from climate_plugin.config_store import (  # noqa: E402
    CLIMATE_AUTH_ENV_VAR,
    read_shell_env_value,
    upsert_shell_env_value,
    write_shell_env_value,
)


class ConfigStoreTests(unittest.TestCase):
    def test_upsert_creates_shell_environment_section_when_missing(self) -> None:
        updated = upsert_shell_env_value("", CLIMATE_AUTH_ENV_VAR, "abc123")
        self.assertIn("[shell_environment_policy.set]", updated)
        self.assertIn('CLIMATE_ECOLOGI_AUTH = "abc123"', updated)

    def test_upsert_preserves_existing_content(self) -> None:
        original = (
            'model = "gpt-5.4"\n'
            "\n"
            "[features]\n"
            "multi_agent = true\n"
            "\n"
            "[shell_environment_policy.set]\n"
            'EXISTING = "1"\n'
        )
        updated = upsert_shell_env_value(original, CLIMATE_AUTH_ENV_VAR, "xyz")
        self.assertIn('model = "gpt-5.4"', updated)
        self.assertIn('EXISTING = "1"', updated)
        self.assertIn('CLIMATE_ECOLOGI_AUTH = "xyz"', updated)

    def test_write_and_read_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.toml"
            config_path.write_text(
                'model = "gpt-5.4"\n\n[shell_environment_policy.set]\nEXISTING = "1"\n'
            )
            write_shell_env_value(config_path, CLIMATE_AUTH_ENV_VAR, "live-token")
            self.assertEqual(
                read_shell_env_value(config_path, CLIMATE_AUTH_ENV_VAR),
                "live-token",
            )


if __name__ == "__main__":
    unittest.main()
