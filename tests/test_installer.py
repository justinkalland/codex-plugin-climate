from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys


INSTALLER_PATH = Path(__file__).resolve().parents[1] / "scripts"
if str(INSTALLER_PATH) not in sys.path:
    sys.path.insert(0, str(INSTALLER_PATH))

from install_climate_plugin import install_plugin  # noqa: E402


class InstallerTests(unittest.TestCase):
    def _create_plugin_fixture(self, root: Path) -> Path:
        plugin_path = root / "plugins" / "climate"
        manifest_dir = plugin_path / ".codex-plugin"
        manifest_dir.mkdir(parents=True)
        (manifest_dir / "plugin.json").write_text('{"name":"climate"}\n')
        return plugin_path

    def test_install_creates_marketplace_file_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plugin_path = self._create_plugin_fixture(root)
            marketplace_path = root / ".agents" / "plugins" / "marketplace.json"

            result = install_plugin(plugin_path, marketplace_path)

            self.assertTrue(result.created_marketplace)
            document = json.loads(marketplace_path.read_text())
            self.assertEqual(document["name"], "local-dev")
            self.assertEqual(document["interface"]["displayName"], "Local Plugins")
            self.assertEqual(document["plugins"][0]["name"], "climate")
            self.assertEqual(
                document["plugins"][0]["source"]["path"],
                str(plugin_path.resolve()),
            )

    def test_install_preserves_existing_marketplace_and_other_plugins(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plugin_path = self._create_plugin_fixture(root)
            marketplace_path = root / ".agents" / "plugins" / "marketplace.json"
            marketplace_path.parent.mkdir(parents=True)
            marketplace_path.write_text(
                json.dumps(
                    {
                        "name": "team-plugins",
                        "interface": {"displayName": "Team Plugins"},
                        "plugins": [
                            {
                                "name": "existing-plugin",
                                "source": {"source": "local", "path": "/tmp/existing"},
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n"
            )

            result = install_plugin(plugin_path, marketplace_path)

            self.assertFalse(result.created_marketplace)
            document = json.loads(marketplace_path.read_text())
            self.assertEqual(document["name"], "team-plugins")
            self.assertEqual(document["interface"]["displayName"], "Team Plugins")
            self.assertEqual(len(document["plugins"]), 2)
            self.assertEqual(document["plugins"][0]["name"], "existing-plugin")
            self.assertEqual(document["plugins"][1]["name"], "climate")

    def test_install_updates_existing_climate_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plugin_path = self._create_plugin_fixture(root)
            marketplace_path = root / ".agents" / "plugins" / "marketplace.json"
            marketplace_path.parent.mkdir(parents=True)
            marketplace_path.write_text(
                json.dumps(
                    {
                        "name": "local-dev",
                        "interface": {"displayName": "Local Plugins"},
                        "plugins": [
                            {
                                "name": "climate",
                                "source": {"source": "local", "path": "/old/path"},
                                "policy": {
                                    "installation": "AVAILABLE",
                                    "authentication": "ON_INSTALL",
                                },
                                "category": "Old Category",
                            }
                        ],
                    },
                    indent=2,
                )
                + "\n"
            )

            install_plugin(plugin_path, marketplace_path)

            document = json.loads(marketplace_path.read_text())
            self.assertEqual(len(document["plugins"]), 1)
            self.assertEqual(
                document["plugins"][0]["source"]["path"],
                str(plugin_path.resolve()),
            )
            self.assertEqual(document["plugins"][0]["category"], "Productivity")

    def test_install_rejects_invalid_marketplace_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plugin_path = self._create_plugin_fixture(root)
            marketplace_path = root / ".agents" / "plugins" / "marketplace.json"
            marketplace_path.parent.mkdir(parents=True)
            marketplace_path.write_text('{"name":"broken","plugins":{}}\n')

            with self.assertRaises(ValueError):
                install_plugin(plugin_path, marketplace_path)


if __name__ == "__main__":
    unittest.main()
