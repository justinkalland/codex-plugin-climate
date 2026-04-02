from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys


SCRIPTS_PATH = Path(__file__).resolve().parents[1] / "plugins" / "climate" / "scripts"
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

from climate_plugin.repo_docs import (  # noqa: E402
    README_END,
    README_START,
    is_managed_climate,
    load_state,
    sync_repo_files,
)


def _live_tree_result() -> dict[str, str]:
    return {
        "provider": "ecologi",
        "action": "plant-tree",
        "actionLabel": "Tree planting",
        "normalizedQuantity": "2",
        "amount": "1.8",
        "currency": "GBP",
        "treeUrl": "https://ecologi.com/test?tree=604a74856345f7001caff578",
        "idempotencyKey": "abc-123",
        "occurredAtUtc": "2026-03-31 10:00",
    }


def _live_avoidance_result() -> dict[str, str]:
    return {
        "provider": "ecologi",
        "action": "carbon-avoidance",
        "actionLabel": "Carbon avoidance",
        "normalizedQuantity": "100",
        "amount": "0.9",
        "currency": "GBP",
        "projectDetails": [
            {
                "name": "Peatland restoration and conservation in Indonesia",
                "projectUrl": "https://ecologi.com/projects/peatland-restoration-in-indonesia",
            }
        ],
        "idempotencyKey": "avoid-123",
        "occurredAtUtc": "2026-03-31 11:00",
    }


def _live_removal_result() -> dict[str, str]:
    return {
        "provider": "ecologi",
        "action": "carbon-removal",
        "actionLabel": "Carbon removal",
        "normalizedQuantity": "10",
        "amount": "1.85",
        "currency": "GBP",
        "tileUrl": "https://ecologi.com/test?tileId=604a74856345f7001caff578",
        "idempotencyKey": "remove-123",
        "occurredAtUtc": "2026-03-31 12:00",
    }


class RepoDocsTests(unittest.TestCase):
    def test_init_without_readme_creates_managed_climate_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            result = sync_repo_files(repo_root)
            climate_text = (repo_root / "CLIMATE.md").read_text()

            self.assertEqual(result["climateStatus"], "created")
            self.assertEqual(result["readmeStatus"], "missing")
            self.assertTrue(is_managed_climate(climate_text))
            self.assertTrue(climate_text.startswith("# 🌍🌱 Climate Action\n"))
            self.assertEqual(load_state(climate_text)["totals"]["trees"], 0)

    def test_init_creates_repo_root_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "new-repo"
            result = sync_repo_files(repo_root)

            self.assertEqual(result["climateStatus"], "created")
            self.assertTrue(repo_root.exists())
            self.assertTrue((repo_root / "CLIMATE.md").exists())

    def test_init_with_readme_appends_managed_section(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / "README.md").write_text("# Demo\n")
            result = sync_repo_files(repo_root)
            readme_text = (repo_root / "README.md").read_text()

            self.assertEqual(result["climateStatus"], "created")
            self.assertEqual(result["readmeStatus"], "appended")
            self.assertIn(README_START, readme_text)
            self.assertIn(README_END, readme_text)
            self.assertIn("## 🌍🌱 Climate Action", readme_text)

    def test_live_update_on_managed_climate_never_rewrites_readme(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / "README.md").write_text("# Demo\n")
            sync_repo_files(repo_root)
            readme_before = (repo_root / "README.md").read_text()

            result = sync_repo_files(repo_root, live_result=_live_tree_result())
            readme_after = (repo_root / "README.md").read_text()
            state = load_state((repo_root / "CLIMATE.md").read_text())

            self.assertEqual(result["climateStatus"], "updated")
            self.assertEqual(result["readmeStatus"], "skipped-existing-climate")
            self.assertEqual(readme_before, readme_after)
            self.assertEqual(state["totals"]["trees"], 2)
            self.assertEqual(len(state["log"]), 1)

    def test_live_update_preserves_existing_managed_climate_title(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            sync_repo_files(repo_root)
            climate_path = repo_root / "CLIMATE.md"
            climate_path.write_text(
                climate_path.read_text().replace(
                    "# 🌍🌱 Climate Action",
                    "# Climate Action",
                    1,
                )
            )

            sync_repo_files(repo_root, live_result=_live_tree_result())
            climate_text = climate_path.read_text()

            self.assertTrue(climate_text.startswith("# Climate Action\n"))

    def test_unmanaged_existing_climate_skips_both_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            (repo_root / "CLIMATE.md").write_text("# Manual climate notes\n")
            (repo_root / "README.md").write_text("# Demo\n")

            result = sync_repo_files(repo_root, live_result=_live_tree_result())

            self.assertEqual(result["climateStatus"], "skipped-unmanaged-existing")
            self.assertEqual(result["readmeStatus"], "skipped-existing-climate")
            self.assertIn("not managed by Climate", result["message"])
            self.assertEqual((repo_root / "README.md").read_text(), "# Demo\n")

    def test_repeated_live_updates_accumulate_totals(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            sync_repo_files(repo_root, live_result=_live_tree_result())
            sync_repo_files(repo_root, live_result=_live_avoidance_result())
            state = load_state((repo_root / "CLIMATE.md").read_text())

            self.assertEqual(state["totals"]["trees"], 2)
            self.assertEqual(state["totals"]["carbonAvoidanceKg"], "100")
            self.assertEqual(len(state["log"]), 2)

    def test_tree_reference_uses_query_id_as_link_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            sync_repo_files(repo_root, live_result=_live_tree_result())
            climate_text = (repo_root / "CLIMATE.md").read_text()

            self.assertIn(
                "[604a74856345f7001caff578](https://ecologi.com/test?tree=604a74856345f7001caff578)",
                climate_text,
            )

    def test_avoidance_reference_uses_project_url_and_generated_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            sync_repo_files(repo_root, live_result=_live_avoidance_result())
            climate_text = (repo_root / "CLIMATE.md").read_text()

            self.assertRegex(
                climate_text,
                r"\[[0-9a-f]{24}\]\(https://ecologi\.com/projects/peatland-restoration-in-indonesia\)",
            )

    def test_removal_reference_uses_tile_id_as_link_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            sync_repo_files(repo_root, live_result=_live_removal_result())
            climate_text = (repo_root / "CLIMATE.md").read_text()

            self.assertIn(
                "[604a74856345f7001caff578](https://ecologi.com/test?tileId=604a74856345f7001caff578)",
                climate_text,
            )


if __name__ == "__main__":
    unittest.main()
