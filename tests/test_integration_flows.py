from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock
import sys


SCRIPTS_PATH = Path(__file__).resolve().parents[1] / "plugins" / "climate" / "scripts"
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

from climate_plugin import cli  # noqa: E402


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class _FakeOpener:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def open(self, request):  # noqa: ANN001
        return _FakeResponse(self.payload)


class IntegrationFlowTests(unittest.TestCase):
    def test_preview_mode_is_non_mutating(self) -> None:
        fake_opener = _FakeOpener({"amount": 0.6, "currency": "GBP"})
        stdout = io.StringIO()
        stderr = io.StringIO()

        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch(
                "climate_plugin.providers.urllib.request.build_opener",
                return_value=fake_opener,
            ):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = cli.main(
                        [
                            "purchase",
                            "--action",
                            "plant-tree",
                            "--quantity",
                            "1",
                            "--mode",
                            "preview",
                            "--repo-root",
                            temp_dir,
                            "--api-key",
                            "preview-key",
                        ]
                    )

            self.assertEqual(exit_code, 0)
            self.assertFalse((Path(temp_dir) / "CLIMATE.md").exists())
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["amount"], 0.6)
            self.assertEqual(payload["currency"], "GBP")
            self.assertNotIn("treeUrl", payload)

    def test_live_mode_creates_repo_files(self) -> None:
        fake_opener = _FakeOpener(
            {
                "amount": 1.8,
                "currency": "GBP",
                "treeUrl": "https://example.com/tree",
                "projectDetails": [{"name": "Forest"}],
            }
        )
        stdout = io.StringIO()
        stderr = io.StringIO()

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / "README.md").write_text("# Demo\n")

            with mock.patch(
                "climate_plugin.providers.urllib.request.build_opener",
                return_value=fake_opener,
            ):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = cli.main(
                        [
                            "purchase",
                            "--action",
                            "plant-tree",
                            "--quantity",
                            "2",
                            "--mode",
                            "live",
                            "--confirm-live",
                            "--repo-root",
                            temp_dir,
                            "--api-key",
                            "live-key",
                        ]
                    )

            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["climateStatus"], "created")
            self.assertTrue((repo_root / "CLIMATE.md").exists())
            self.assertIn("Climate Action", (repo_root / "README.md").read_text())

    def test_simulate_preview_succeeds_offline_and_does_not_create_repo_files(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with tempfile.TemporaryDirectory() as temp_dir:
            with mock.patch(
                "climate_plugin.providers.urllib.request.build_opener",
                side_effect=AssertionError("network opener should not be used"),
            ):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = cli.main(
                        [
                            "purchase",
                            "--action",
                            "plant-tree",
                            "--quantity",
                            "1",
                            "--mode",
                            "preview",
                            "--repo-root",
                            temp_dir,
                            "--api-key",
                            "SIMULATE",
                        ]
                    )

            self.assertEqual(exit_code, 0)
            self.assertFalse((Path(temp_dir) / "CLIMATE.md").exists())
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["amount"], 0.8)
            self.assertEqual(payload["currency"], "USD")

    def test_simulate_live_creates_repo_files_offline(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()

        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / "README.md").write_text("# Demo\n")

            with mock.patch(
                "climate_plugin.providers.urllib.request.build_opener",
                side_effect=AssertionError("network opener should not be used"),
            ):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = cli.main(
                        [
                            "purchase",
                            "--action",
                            "plant-tree",
                            "--quantity",
                            "1",
                            "--mode",
                            "live",
                            "--confirm-live",
                            "--repo-root",
                            temp_dir,
                            "--api-key",
                            "SIMULATE",
                        ]
                    )

            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["amount"], 0.8)
            self.assertEqual(payload["currency"], "USD")
            self.assertEqual(payload["climateStatus"], "created")
            self.assertTrue((repo_root / "CLIMATE.md").exists())
            self.assertIn(
                "[604a74856345f7001caff578](https://ecologi.com/test?tree=604a74856345f7001caff578)",
                (repo_root / "CLIMATE.md").read_text(),
            )
            self.assertIn("Climate Action", (repo_root / "README.md").read_text())


if __name__ == "__main__":
    unittest.main()
