from __future__ import annotations

import json
import hashlib
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import re
from typing import Any
from urllib.parse import parse_qs, urlparse


CLIMATE_MANAGED_MARKER = "<!-- climate:managed -->"
CLIMATE_DATA_START = "<!-- climate:data:start"
CLIMATE_DATA_END = "climate:data:end -->"
README_START = "<!-- climate:readme:start -->"
README_END = "<!-- climate:readme:end -->"
CLIMATE_TITLE = "# 🌍🌱 Climate Action"
README_TITLE = "## 🌍🌱 Climate Action"


def _default_state() -> dict[str, Any]:
    return {
        "version": 1,
        "totals": {
            "trees": 0,
            "carbonAvoidanceKg": "0",
            "carbonRemovalKg": "0",
        },
        "log": [],
    }


def _format_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized.quantize(Decimal("1")), "f")
    text = format(normalized, "f")
    return text.rstrip("0").rstrip(".")


def _format_quantity(action: str, normalized_quantity: str) -> str:
    value = Decimal(normalized_quantity)
    if action == "plant-tree":
        count = int(value)
        noun = "tree" if count == 1 else "trees"
        return f"{count} {noun}"
    return f"{_format_decimal(value)} kg CO2e"


def is_managed_climate(text: str) -> bool:
    return (
        CLIMATE_MANAGED_MARKER in text
        and CLIMATE_DATA_START in text
        and CLIMATE_DATA_END in text
    )


def load_state(text: str) -> dict[str, Any]:
    if not is_managed_climate(text):
        raise ValueError("CLIMATE.md is not managed by the Climate plugin.")
    match = re.search(
        re.escape(CLIMATE_DATA_START) + r"\n(.*?)\n" + re.escape(CLIMATE_DATA_END),
        text,
        re.DOTALL,
    )
    if not match:
        raise ValueError("Managed CLIMATE.md is missing state data.")
    return json.loads(match.group(1))


def _render_summary(state: dict[str, Any]) -> list[str]:
    totals = state["totals"]
    return [
        "## Summary",
        f"- Trees planted: {totals['trees']}",
        f"- Carbon avoidance purchased: {_format_decimal(Decimal(totals['carbonAvoidanceKg']))} kg CO2e",
        f"- Carbon removal purchased: {_format_decimal(Decimal(totals['carbonRemovalKg']))} kg CO2e",
    ]


def _render_log(state: dict[str, Any]) -> list[str]:
    lines = ["## Impact Log"]
    if not state["log"]:
        lines.append("_No live climate actions recorded yet._")
        return lines

    lines.extend(
        [
            "| Date (UTC) | Provider | Action | Quantity | Cost | Reference |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for entry in state["log"]:
        reference = _render_reference(entry)
        lines.append(
            "| "
            + " | ".join(
                [
                    entry["occurredAtUtc"],
                    entry["provider"],
                    entry["actionLabel"],
                    _format_quantity(entry["action"], entry["normalizedQuantity"]),
                    f"{entry['amount']} {entry['currency']}",
                    reference,
                ]
            )
            + " |"
        )
    return lines


def _project_url_from_details(project_details: Any) -> str | None:
    if not isinstance(project_details, list):
        return None
    for project in project_details:
        if isinstance(project, dict):
            project_url = project.get("projectUrl")
            if project_url:
                return str(project_url)
    return None


def _reference_url_for_result(result: dict[str, Any]) -> str | None:
    return (
        result.get("treeUrl")
        or result.get("tileUrl")
        or _project_url_from_details(result.get("projectDetails"))
    )


def _reference_text_for_url(reference_url: str) -> str:
    parsed = urlparse(reference_url)
    query = parse_qs(parsed.query)
    tree_id = query.get("tree", [None])[0]
    if tree_id:
        return tree_id
    tile_id = query.get("tileId", [None])[0]
    if tile_id:
        return tile_id
    return hashlib.sha1(reference_url.encode("utf-8")).hexdigest()[:24]


def _render_reference(entry: dict[str, Any]) -> str:
    reference_url = entry.get("referenceUrl")
    if not reference_url:
        return "-"
    reference_text = entry.get("referenceText") or _reference_text_for_url(reference_url)
    return f"[{reference_text}]({reference_url})"


def _extract_climate_title(text: str) -> str:
    first_line = text.splitlines()[0].strip() if text.splitlines() else ""
    if first_line.startswith("# "):
        return first_line
    return CLIMATE_TITLE


def render_climate_markdown(state: dict[str, Any], *, title: str = CLIMATE_TITLE) -> str:
    state_json = json.dumps(state, indent=2, sort_keys=True)
    lines = [
        title,
        "",
        CLIMATE_MANAGED_MARKER,
        CLIMATE_DATA_START,
        state_json,
        CLIMATE_DATA_END,
        "",
        "This file is managed by the Climate plugin.",
        "",
        *_render_summary(state),
        "",
        "## Estimated Footprint",
        "_Not implemented yet._",
        "",
        *_render_log(state),
        "",
    ]
    return "\n".join(lines)


def _append_readme_section(readme_text: str) -> tuple[str, str]:
    if README_START in readme_text and README_END in readme_text:
        return readme_text, "already-managed"
    if re.search(r"(?mi)^#{1,6}\s+Climate Action\s*$", readme_text):
        return readme_text, "existing-climate-section"

    trimmed = readme_text.rstrip()
    if trimmed:
        trimmed += "\n\n"
    section = "\n".join(
        [
            README_START,
            README_TITLE,
            "This project tracks positive climate action taken through the Climate plugin.",
            "See [CLIMATE.md](CLIMATE.md) for totals and history.",
            README_END,
            "",
        ]
    )
    return trimmed + section, "appended"


def _apply_live_result(state: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    updated = deepcopy(state)
    normalized_quantity = Decimal(result["normalizedQuantity"])
    reference_url = _reference_url_for_result(result)

    if result["action"] == "plant-tree":
        updated["totals"]["trees"] += int(normalized_quantity)
    elif result["action"] == "carbon-avoidance":
        total = Decimal(updated["totals"]["carbonAvoidanceKg"]) + normalized_quantity
        updated["totals"]["carbonAvoidanceKg"] = _format_decimal(total)
    elif result["action"] == "carbon-removal":
        total = Decimal(updated["totals"]["carbonRemovalKg"]) + normalized_quantity
        updated["totals"]["carbonRemovalKg"] = _format_decimal(total)

    updated["log"].append(
        {
            "provider": result["provider"],
            "action": result["action"],
            "actionLabel": result["actionLabel"],
            "normalizedQuantity": result["normalizedQuantity"],
            "amount": result["amount"],
            "currency": result["currency"],
            "occurredAtUtc": result.get(
                "occurredAtUtc",
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            ),
            "referenceUrl": reference_url,
            "referenceText": (
                _reference_text_for_url(reference_url) if reference_url else None
            ),
            "idempotencyKey": result.get("idempotencyKey"),
        }
    )
    return updated


def sync_repo_files(
    repo_root: Path,
    *,
    live_result: dict[str, Any] | None = None,
) -> dict[str, str]:
    repo_root = repo_root.resolve()
    repo_root.mkdir(parents=True, exist_ok=True)
    climate_path = repo_root / "CLIMATE.md"
    readme_path = repo_root / "README.md"

    statuses = {
        "climateStatus": "unchanged",
        "readmeStatus": "unchanged",
        "message": "",
    }

    if climate_path.exists():
        existing_text = climate_path.read_text()
        if not is_managed_climate(existing_text):
            statuses["climateStatus"] = "skipped-unmanaged-existing"
            statuses["readmeStatus"] = "skipped-existing-climate"
            statuses["message"] = (
                "CLIMATE.md already exists and is not managed by Climate, so it was not edited."
            )
            return statuses

        state = load_state(existing_text)
        if live_result is not None:
            state = _apply_live_result(state, live_result)
            climate_path.write_text(
                render_climate_markdown(state, title=_extract_climate_title(existing_text))
            )
            statuses["climateStatus"] = "updated"
        else:
            statuses["climateStatus"] = "already-managed"
        statuses["readmeStatus"] = "skipped-existing-climate"
        return statuses

    state = _default_state()
    if live_result is not None:
        state = _apply_live_result(state, live_result)
    climate_path.write_text(render_climate_markdown(state))
    statuses["climateStatus"] = "created"

    if readme_path.exists():
        readme_text, readme_status = _append_readme_section(readme_path.read_text())
        if readme_status == "appended":
            readme_path.write_text(readme_text)
        statuses["readmeStatus"] = readme_status
    else:
        statuses["readmeStatus"] = "missing"

    return statuses
