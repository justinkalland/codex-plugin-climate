from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


BASE_URL = "https://public.ecologi.com"
SIMULATE_API_KEY = "SIMULATE"
SIMULATED_CURRENCY = "USD"
SIMULATED_TREE_PRICE_USD = Decimal("0.80")
SIMULATED_AVOIDANCE_PRICE_PER_TONNE_USD = Decimal("12.50")
SIMULATED_AVOIDANCE_PRICE_PER_KG_USD = Decimal("0.0125")
SIMULATED_REMOVAL_PRICE_PER_KG_USD = Decimal("0.28")
SIMULATED_TREE_URL = "https://ecologi.com/test?tree=604a74856345f7001caff578"
SIMULATED_TILE_URL = "https://ecologi.com/test?tileId=604a74856345f7001caff578"
SIMULATED_TREE_PROJECT_URL = "https://ecologi.com/projects/forest-restoration-in-kenya"
SIMULATED_AVOIDANCE_PROJECT_URL = (
    "https://ecologi.com/projects/peatland-restoration-in-indonesia"
)
SIMULATED_REMOVAL_PROJECT_URL = "https://ecologi.com/projects/biochar-carbon-removal"

ACTION_TREE = "plant-tree"
ACTION_AVOIDANCE = "carbon-avoidance"
ACTION_REMOVAL = "carbon-removal"

SUPPORTED_ACTIONS = {ACTION_TREE, ACTION_AVOIDANCE, ACTION_REMOVAL}
SUPPORTED_PROVIDERS = {"ecologi"}


class ClimateError(RuntimeError):
    """Base runtime error for climate actions."""


class ValidationError(ClimateError):
    """Raised when a request is invalid before contacting a provider."""


@dataclass
class PreparedRequest:
    provider: str
    action: str
    endpoint: str
    payload: dict[str, Any]
    normalized_quantity: Decimal
    normalized_unit: str
    quantity_display: str
    action_label: str


def _parse_decimal(raw_quantity: str) -> Decimal:
    try:
        quantity = Decimal(str(raw_quantity))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"Invalid quantity: {raw_quantity}") from exc
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than zero.")
    return quantity


def _format_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized.quantize(Decimal("1")), "f")
    text = format(normalized, "f")
    return text.rstrip("0").rstrip(".")


def _quantize_currency(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _currency_number(amount: Decimal) -> float:
    return float(_quantize_currency(amount))


def _display_trees(quantity: Decimal) -> str:
    count = int(quantity)
    noun = "tree" if count == 1 else "trees"
    return f"{count} {noun}"


def _display_kg(quantity: Decimal) -> str:
    return f"{_format_decimal(quantity)} kg CO2e"


def _normalize_units(units: str | None, *, allow_none: bool = False) -> str | None:
    if units is None:
        return None if allow_none else "kg"
    lowered = units.strip().lower()
    if lowered not in {"kg", "tonnes"}:
        raise ValidationError("Units must be either 'kg' or 'tonnes'.")
    return lowered


def _as_integral_quantity(quantity: Decimal, noun: str) -> int:
    if quantity != quantity.to_integral():
        raise ValidationError(f"{noun} quantity must be a whole number.")
    whole = int(quantity)
    if whole < 1:
        raise ValidationError(f"{noun} quantity must be at least 1.")
    return whole


def prepare_ecologi_request(
    *,
    action: str,
    quantity: str,
    units: str | None = None,
    name: str | None = None,
    preview: bool,
) -> PreparedRequest:
    if action not in SUPPORTED_ACTIONS:
        raise ValidationError(f"Unsupported action: {action}")

    parsed_quantity = _parse_decimal(quantity)
    payload: dict[str, Any]

    if action == ACTION_TREE:
        number = _as_integral_quantity(parsed_quantity, "Tree")
        payload = {"number": number, "test": preview}
        if name:
            payload["name"] = name
        return PreparedRequest(
            provider="ecologi",
            action=action,
            endpoint="/impact/trees",
            payload=payload,
            normalized_quantity=Decimal(number),
            normalized_unit="trees",
            quantity_display=_display_trees(Decimal(number)),
            action_label="Tree planting",
        )

    normalized_units = _normalize_units(units)
    if action == ACTION_AVOIDANCE:
        if normalized_units == "kg" and parsed_quantity < Decimal("1"):
            raise ValidationError("Carbon avoidance must be at least 1 kg.")
        if normalized_units == "tonnes" and parsed_quantity < Decimal("0.001"):
            raise ValidationError("Carbon avoidance must be at least 0.001 tonnes.")
        payload = {
            "number": int(parsed_quantity) if parsed_quantity == parsed_quantity.to_integral() else float(parsed_quantity),
            "units": "KG" if normalized_units == "kg" else "Tonnes",
            "test": preview,
        }
        if name:
            payload["name"] = name
        normalized_quantity = (
            parsed_quantity
            if normalized_units == "kg"
            else parsed_quantity * Decimal("1000")
        )
        return PreparedRequest(
            provider="ecologi",
            action=action,
            endpoint="/impact/carbon",
            payload=payload,
            normalized_quantity=normalized_quantity,
            normalized_unit="kg",
            quantity_display=_display_kg(normalized_quantity),
            action_label="Carbon avoidance",
        )

    removal_kg = parsed_quantity
    if normalized_units == "tonnes":
        removal_kg = parsed_quantity * Decimal("1000")
    if removal_kg != removal_kg.to_integral():
        raise ValidationError(
            "Carbon removal must resolve to a whole number of kilograms."
        )
    if removal_kg < 1:
        raise ValidationError("Carbon removal must be at least 1 kg.")
    payload = {"number": int(removal_kg), "test": preview}
    if name:
        payload["name"] = name
    return PreparedRequest(
        provider="ecologi",
        action=action,
        endpoint="/impact/carbon-removal",
        payload=payload,
        normalized_quantity=removal_kg,
        normalized_unit="kg",
        quantity_display=_display_kg(removal_kg),
        action_label="Carbon removal",
    )


class EcologiClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = BASE_URL,
        opener: Any | None = None,
    ) -> None:
        if not api_key:
            raise ValidationError("Missing Ecologi API key.")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.opener = opener or urllib.request.build_opener()

    def purchase(self, prepared: PreparedRequest, *, preview: bool) -> dict[str, Any]:
        idempotency_key = str(uuid.uuid4())
        body = json.dumps(prepared.payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{prepared.endpoint}",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Idempotency-Key": idempotency_key,
            },
            method="POST",
        )

        try:
            response = self.opener.open(request)
            payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ClimateError(
                f"Ecologi request failed with HTTP {exc.code}: {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ClimateError(f"Ecologi request failed: {exc.reason}") from exc

        result = {
            "provider": prepared.provider,
            "action": prepared.action,
            "actionLabel": prepared.action_label,
            "preview": preview,
            "amount": payload.get("amount"),
            "currency": payload.get("currency"),
            "normalizedQuantity": _format_decimal(prepared.normalized_quantity),
            "normalizedUnit": prepared.normalized_unit,
            "quantityDisplay": prepared.quantity_display,
            "fundedBy": prepared.payload.get("name"),
        }
        if preview:
            return {
                "amount": result["amount"],
                "currency": result["currency"],
            }

        result.update(
            {
                "idempotencyKey": idempotency_key,
                "projectDetails": payload.get("projectDetails", []),
                "treeUrl": payload.get("treeUrl"),
                "tileUrl": payload.get("tileUrl"),
            }
        )
        return result


class SimulatedEcologiClient:
    def __init__(self, *, api_key: str) -> None:
        if api_key != SIMULATE_API_KEY:
            raise ValidationError("Simulated Ecologi client requires the SIMULATE key.")
        self.api_key = api_key

    def purchase(self, prepared: PreparedRequest, *, preview: bool) -> dict[str, Any]:
        amount = self._price(prepared)
        result = {
            "provider": prepared.provider,
            "action": prepared.action,
            "actionLabel": prepared.action_label,
            "preview": preview,
            "amount": _currency_number(amount),
            "currency": SIMULATED_CURRENCY,
            "normalizedQuantity": _format_decimal(prepared.normalized_quantity),
            "normalizedUnit": prepared.normalized_unit,
            "quantityDisplay": prepared.quantity_display,
            "fundedBy": prepared.payload.get("name"),
        }
        if preview:
            return {
                "amount": result["amount"],
                "currency": result["currency"],
            }

        result.update(
            {
                "idempotencyKey": str(uuid.uuid4()),
                "projectDetails": self._project_details(prepared),
                "treeUrl": self._tree_url(prepared),
                "tileUrl": self._tile_url(prepared),
            }
        )
        return result

    def _price(self, prepared: PreparedRequest) -> Decimal:
        if prepared.action == ACTION_TREE:
            return prepared.normalized_quantity * SIMULATED_TREE_PRICE_USD
        if prepared.action == ACTION_AVOIDANCE:
            return prepared.normalized_quantity * SIMULATED_AVOIDANCE_PRICE_PER_KG_USD
        if prepared.action == ACTION_REMOVAL:
            return prepared.normalized_quantity * SIMULATED_REMOVAL_PRICE_PER_KG_USD
        raise ValidationError(f"Unsupported simulated action: {prepared.action}")

    def _tree_url(self, prepared: PreparedRequest) -> str | None:
        if prepared.action == ACTION_TREE:
            return SIMULATED_TREE_URL
        return None

    def _tile_url(self, prepared: PreparedRequest) -> str | None:
        if prepared.action == ACTION_REMOVAL:
            return SIMULATED_TILE_URL
        return None

    def _project_details(self, prepared: PreparedRequest) -> list[dict[str, Any]]:
        if prepared.action == ACTION_TREE:
            return [
                {
                    "name": "Forest restoration in Kenya",
                    "projectUrl": SIMULATED_TREE_PROJECT_URL,
                    "splitPercentage": 100,
                    "splitAmountTrees": int(prepared.normalized_quantity),
                }
            ]
        if prepared.action == ACTION_AVOIDANCE:
            return [
                {
                    "name": "Peatland restoration and conservation in Indonesia",
                    "projectUrl": SIMULATED_AVOIDANCE_PROJECT_URL,
                    "splitPercentage": 100,
                    "splitAmountTonnes": float(
                        prepared.normalized_quantity / Decimal("1000")
                    ),
                }
            ]
        if prepared.action == ACTION_REMOVAL:
            return [
                {
                    "name": "Biochar carbon removal",
                    "projectUrl": SIMULATED_REMOVAL_PROJECT_URL,
                    "quantity": int(prepared.normalized_quantity),
                }
            ]
        return []


def create_ecologi_client(
    *,
    api_key: str,
    base_url: str = BASE_URL,
    opener: Any | None = None,
) -> EcologiClient | SimulatedEcologiClient:
    if api_key == SIMULATE_API_KEY:
        return SimulatedEcologiClient(api_key=api_key)
    return EcologiClient(api_key=api_key, base_url=base_url, opener=opener)
