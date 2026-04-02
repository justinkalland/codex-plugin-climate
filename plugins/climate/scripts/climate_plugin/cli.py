from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from climate_plugin.config_store import (
    CLIMATE_AUTH_ENV_VAR,
    read_shell_env_value,
    write_shell_env_value,
)
from climate_plugin.providers import (
    ACTION_AVOIDANCE,
    ACTION_REMOVAL,
    ACTION_TREE,
    ClimateError,
    SUPPORTED_PROVIDERS,
    ValidationError,
    create_ecologi_client,
    prepare_ecologi_request,
)
from climate_plugin.repo_docs import sync_repo_files


def _read_api_key(args: argparse.Namespace) -> str:
    if getattr(args, "api_key", None):
        return args.api_key
    if getattr(args, "read_key_stdin", False):
        return sys.stdin.read().strip()
    return ""


def _print_json(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Climate plugin helper CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    configure = subparsers.add_parser(
        "configure-ecologi",
        help="Store the Ecologi API key in the user's Codex config.",
    )
    configure.add_argument("--api-key")
    configure.add_argument("--read-key-stdin", action="store_true")
    configure.add_argument(
        "--config-path",
        default="~/.codex/config.toml",
        help="Path to Codex config.toml",
    )

    purchase = subparsers.add_parser(
        "purchase",
        help="Preview or execute a climate action against a provider.",
    )
    purchase.add_argument("--provider", default="ecologi", choices=sorted(SUPPORTED_PROVIDERS))
    purchase.add_argument(
        "--action",
        required=True,
        choices=[ACTION_TREE, ACTION_AVOIDANCE, ACTION_REMOVAL],
    )
    purchase.add_argument("--quantity", required=True)
    purchase.add_argument("--units")
    purchase.add_argument("--name")
    purchase.add_argument("--mode", choices=["preview", "live"], default="preview")
    purchase.add_argument("--repo-root", help="Project root to initialize/update CLIMATE.md")
    purchase.add_argument("--base-url", default=None)
    purchase.add_argument("--api-key")
    purchase.add_argument("--config-path", default="~/.codex/config.toml")
    purchase.add_argument("--confirm-live", action="store_true")

    init_repo = subparsers.add_parser(
        "init-repo",
        help="Create a managed CLIMATE.md and optional README section in a repo.",
    )
    init_repo.add_argument("--repo-root", default=".")

    estimate = subparsers.add_parser(
        "estimate",
        help="Stubbed emissions estimate command.",
    )
    estimate.add_argument("--repo-root", default=".")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "configure-ecologi":
            api_key = _read_api_key(args)
            if not api_key:
                raise ValidationError("Provide an API key via --api-key or --read-key-stdin.")
            config_path = Path(args.config_path).expanduser()
            write_shell_env_value(config_path, CLIMATE_AUTH_ENV_VAR, api_key)
            return _print_json(
                {
                    "provider": "ecologi",
                    "envVar": CLIMATE_AUTH_ENV_VAR,
                    "configPath": str(config_path),
                    "status": "configured",
                }
            )

        if args.command == "purchase":
            api_key = (
                args.api_key
                or os.getenv(CLIMATE_AUTH_ENV_VAR)
                or read_shell_env_value(Path(args.config_path), CLIMATE_AUTH_ENV_VAR)
            )
            if not api_key:
                raise ValidationError(
                    f"Missing Ecologi credential. Set {CLIMATE_AUTH_ENV_VAR} or pass --api-key."
                )

            preview = args.mode == "preview"
            if not preview and not args.confirm_live:
                raise ValidationError("Live purchases require --confirm-live.")
            prepared = prepare_ecologi_request(
                action=args.action,
                quantity=args.quantity,
                units=args.units,
                name=args.name,
                preview=preview,
            )
            client = create_ecologi_client(
                api_key=api_key,
                base_url=args.base_url or "https://public.ecologi.com",
            )
            result = client.purchase(prepared, preview=preview)
            if not preview and args.repo_root:
                result.update(
                    sync_repo_files(Path(args.repo_root), live_result=result)
                )
            return _print_json(result)

        if args.command == "init-repo":
            result = sync_repo_files(Path(args.repo_root))
            result["repoRoot"] = str(Path(args.repo_root).resolve())
            return _print_json(result)

        if args.command == "estimate":
            return _print_json(
                {
                    "repoRoot": str(Path(args.repo_root).resolve()),
                    "implemented": False,
                    "message": "Repo carbon estimation is not implemented yet.",
                }
            )
    except (ClimateError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "error": str(exc),
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2
