from __future__ import annotations

import json
import re
from pathlib import Path


CLIMATE_AUTH_ENV_VAR = "CLIMATE_ECOLOGI_AUTH"
SHELL_ENV_SET_SECTION = "shell_environment_policy.set"
SECTION_HEADER = f"[{SHELL_ENV_SET_SECTION}]"

_SECTION_HEADER_RE = re.compile(r"^\s*\[(?P<section>[^\]]+)\]\s*$")
_INLINE_SHELL_ENV_RE = re.compile(r"^\s*shell_environment_policy\s*=")
_ENV_LINE_RE_TEMPLATE = r"^\s*{name}\s*="
_VALUE_LINE_RE_TEMPLATE = r"^\s*{name}\s*=\s*(?P<value>.+?)\s*$"


def _toml_basic_string(value: str) -> str:
    return json.dumps(value)


def upsert_shell_env_value(config_text: str, env_name: str, env_value: str) -> str:
    """Insert or replace a value in [shell_environment_policy.set] while preserving other text."""

    lines = config_text.splitlines(keepends=True)
    value_line = f"{env_name} = {_toml_basic_string(env_value)}\n"

    section_start = None
    section_end = None

    for index, line in enumerate(lines):
        match = _SECTION_HEADER_RE.match(line)
        if not match:
            continue
        if match.group("section").strip() == SHELL_ENV_SET_SECTION:
            section_start = index
            break

    if section_start is None:
        for line in lines:
            if _INLINE_SHELL_ENV_RE.match(line):
                raise ValueError(
                    "Unsupported config layout: shell_environment_policy is defined inline. "
                    f"Please add {SECTION_HEADER} manually."
                )

        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        if lines and lines[-1].strip():
            lines.append("\n")
        lines.extend([f"{SECTION_HEADER}\n", value_line])
        return "".join(lines)

    section_end = len(lines)
    for index in range(section_start + 1, len(lines)):
        if _SECTION_HEADER_RE.match(lines[index]):
            section_end = index
            break

    env_line_re = re.compile(_ENV_LINE_RE_TEMPLATE.format(name=re.escape(env_name)))
    for index in range(section_start + 1, section_end):
        if env_line_re.match(lines[index]):
            lines[index] = value_line
            return "".join(lines)

    insert_at = section_end
    lines.insert(insert_at, value_line)
    return "".join(lines)


def write_shell_env_value(config_path: Path, env_name: str, env_value: str) -> None:
    config_path = config_path.expanduser()
    original = config_path.read_text() if config_path.exists() else ""
    updated = upsert_shell_env_value(original, env_name, env_value)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(updated)


def _parse_toml_string(raw_value: str) -> str | None:
    value = raw_value.strip()
    if not value:
        return None
    if value.startswith('"') and value.endswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return str(parsed)
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    return value


def read_shell_env_value(config_path: Path, env_name: str) -> str | None:
    config_path = config_path.expanduser()
    if not config_path.exists():
        return None

    lines = config_path.read_text().splitlines()
    in_target_section = False
    value_line_re = re.compile(_VALUE_LINE_RE_TEMPLATE.format(name=re.escape(env_name)))

    for line in lines:
        section_match = _SECTION_HEADER_RE.match(line)
        if section_match:
            in_target_section = (
                section_match.group("section").strip() == SHELL_ENV_SET_SECTION
            )
            continue

        if not in_target_section:
            continue

        value_match = value_line_re.match(line)
        if not value_match:
            continue

        return _parse_toml_string(value_match.group("value"))

    return None
