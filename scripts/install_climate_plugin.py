#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MIN_PYTHON = (3, 10)
DEFAULT_MARKETPLACE_NAME = "local-dev"
DEFAULT_MARKETPLACE_DISPLAY_NAME = "Local Plugins"
PLUGIN_NAME = "climate"
PLUGIN_CATEGORY = "Productivity"


@dataclass(frozen=True)
class InstallResult:
    marketplace_path: Path
    marketplace_name: str
    marketplace_display_name: str
    plugin_path: Path
    created_marketplace: bool
    changed: bool


def _default_marketplace_document() -> dict[str, Any]:
    return {
        "name": DEFAULT_MARKETPLACE_NAME,
        "interface": {"displayName": DEFAULT_MARKETPLACE_DISPLAY_NAME},
        "plugins": [],
    }


def _ensure_marketplace_document_shape(
    document: dict[str, Any], marketplace_path: Path
) -> dict[str, Any]:
    plugins = document.get("plugins")
    if plugins is None:
        document["plugins"] = []
        plugins = document["plugins"]
    if not isinstance(plugins, list):
        raise ValueError(f"{marketplace_path} has an invalid 'plugins' field; expected a list.")

    for index, plugin in enumerate(plugins):
        if not isinstance(plugin, dict):
            raise ValueError(
                f"{marketplace_path} has an invalid plugin entry at index {index}; "
                "expected an object."
            )

    if not isinstance(document.get("name"), str) or not document["name"].strip():
        document["name"] = DEFAULT_MARKETPLACE_NAME

    interface = document.get("interface")
    if interface is None:
        document["interface"] = {"displayName": DEFAULT_MARKETPLACE_DISPLAY_NAME}
    elif not isinstance(interface, dict):
        raise ValueError(
            f"{marketplace_path} has an invalid 'interface' field; expected an object."
        )
    else:
        display_name = interface.get("displayName")
        if not isinstance(display_name, str) or not display_name.strip():
            interface["displayName"] = DEFAULT_MARKETPLACE_DISPLAY_NAME

    return document


def _load_marketplace_document(marketplace_path: Path) -> tuple[dict[str, Any], bool]:
    if not marketplace_path.exists():
        return _default_marketplace_document(), True

    try:
        document = json.loads(marketplace_path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{marketplace_path} is not valid JSON. Fix it or remove it and try again."
        ) from exc

    if not isinstance(document, dict):
        raise ValueError(f"{marketplace_path} must contain a JSON object at the top level.")

    return _ensure_marketplace_document_shape(document, marketplace_path), False


def _upsert_climate_plugin_entry(
    document: dict[str, Any], plugin_path: Path
) -> tuple[dict[str, Any], bool]:
    plugins = document["plugins"]
    plugin_path_str = str(plugin_path)
    plugin_index = next(
        (index for index, plugin in enumerate(plugins) if plugin.get("name") == PLUGIN_NAME),
        None,
    )

    if plugin_index is None:
        entry: dict[str, Any] = {}
        plugins.append(entry)
    else:
        entry = plugins[plugin_index]

    before = deepcopy(entry)

    entry["name"] = PLUGIN_NAME

    source = entry.get("source")
    if not isinstance(source, dict):
        source = {}
    source["source"] = "local"
    source["path"] = plugin_path_str
    entry["source"] = source

    policy = entry.get("policy")
    if not isinstance(policy, dict):
        policy = {}
    policy["installation"] = "AVAILABLE"
    policy["authentication"] = "ON_INSTALL"
    entry["policy"] = policy

    entry["category"] = PLUGIN_CATEGORY

    return document, before != entry


def install_plugin(plugin_path: Path, marketplace_path: Path) -> InstallResult:
    plugin_path = plugin_path.expanduser().resolve()
    marketplace_path = marketplace_path.expanduser()

    manifest_path = plugin_path / ".codex-plugin" / "plugin.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Could not find Climate plugin manifest at {manifest_path}")

    document, created_marketplace = _load_marketplace_document(marketplace_path)
    document, changed = _upsert_climate_plugin_entry(document, plugin_path)

    marketplace_path.parent.mkdir(parents=True, exist_ok=True)
    marketplace_path.write_text(json.dumps(document, indent=2) + "\n")

    return InstallResult(
        marketplace_path=marketplace_path,
        marketplace_name=document["name"],
        marketplace_display_name=document["interface"]["displayName"],
        plugin_path=plugin_path,
        created_marketplace=created_marketplace,
        changed=changed or created_marketplace,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[1]

    parser = argparse.ArgumentParser(
        description=(
            "Add the Climate plugin to the user-level Codex marketplace so it can be "
            "installed across projects."
        )
    )
    parser.add_argument(
        "--plugin-path",
        type=Path,
        default=repo_root / "plugins" / "climate",
        help="Absolute or relative path to the Climate plugin directory.",
    )
    parser.add_argument(
        "--marketplace-path",
        type=Path,
        default=Path.home() / ".agents" / "plugins" / "marketplace.json",
        help="Path to the user-level Codex marketplace JSON file.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if sys.version_info < MIN_PYTHON:
        sys.stderr.write(
            "Climate requires Python 3.10 or newer. "
            "Use python3, python, or py -3 with a supported Python 3 installation.\n"
        )
        return 1

    args = parse_args(argv)

    try:
        result = install_plugin(args.plugin_path, args.marketplace_path)
    except (FileNotFoundError, ValueError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    if result.created_marketplace:
        status = "Created"
    elif result.changed:
        status = "Updated"
    else:
        status = "Verified"
    sys.stdout.write(
        f"{status} {result.marketplace_path} for the Climate plugin.\n"
        f"Marketplace: {result.marketplace_display_name} ({result.marketplace_name})\n"
        f"Plugin path: {result.plugin_path}\n\n"
        "Next:\n"
        "1. Open Codex.\n"
        "2. Open Plugins.\n"
        f"3. Choose the '{result.marketplace_display_name}' marketplace.\n"
        "4. Install or refresh Climate.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
