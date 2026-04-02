from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS_PATH = Path(__file__).resolve().parents[1] / "plugins" / "climate" / "scripts"
if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

from climate_plugin.providers import (  # noqa: E402
    ACTION_AVOIDANCE,
    ACTION_REMOVAL,
    ACTION_TREE,
    EcologiClient,
    SIMULATE_API_KEY,
    ValidationError,
    create_ecologi_client,
    prepare_ecologi_request,
)


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class _FakeOpener:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.last_request = None

    def open(self, request):  # noqa: ANN001
        self.last_request = request
        return _FakeResponse(self.payload)


class ProviderLogicTests(unittest.TestCase):
    def test_tree_request_payload_is_built_for_preview(self) -> None:
        prepared = prepare_ecologi_request(
            action=ACTION_TREE,
            quantity="2",
            preview=True,
        )
        self.assertEqual(prepared.endpoint, "/impact/trees")
        self.assertEqual(prepared.payload["number"], 2)
        self.assertTrue(prepared.payload["test"])
        self.assertEqual(prepared.quantity_display, "2 trees")

    def test_removal_allows_tonnes_when_they_convert_to_whole_kilograms(self) -> None:
        prepared = prepare_ecologi_request(
            action=ACTION_REMOVAL,
            quantity="0.5",
            units="tonnes",
            preview=False,
        )
        self.assertEqual(prepared.payload["number"], 500)
        self.assertEqual(prepared.normalized_unit, "kg")
        self.assertEqual(prepared.quantity_display, "500 kg CO2e")

    def test_fractional_tree_quantity_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            prepare_ecologi_request(
                action=ACTION_TREE,
                quantity="1.5",
                preview=True,
            )

    def test_preview_response_strips_live_only_fields(self) -> None:
        opener = _FakeOpener(
            {
                "amount": 1.8,
                "currency": "GBP",
                "treeUrl": "https://example.com/tree",
                "projectDetails": [{"name": "Forest"}],
            }
        )
        client = EcologiClient(api_key="test-key", opener=opener)
        prepared = prepare_ecologi_request(
            action=ACTION_TREE,
            quantity="1",
            preview=True,
        )
        result = client.purchase(prepared, preview=True)
        self.assertEqual(result["amount"], 1.8)
        self.assertEqual(result["currency"], "GBP")
        self.assertNotIn("treeUrl", result)
        self.assertNotIn("projectDetails", result)

    def test_live_response_includes_reference_and_headers(self) -> None:
        opener = _FakeOpener(
            {
                "amount": 9.2,
                "currency": "USD",
                "tileUrl": "https://example.com/tile",
                "projectDetails": [{"name": "Biochar"}],
            }
        )
        client = EcologiClient(api_key="live-key", opener=opener)
        prepared = prepare_ecologi_request(
            action=ACTION_REMOVAL,
            quantity="25",
            units="kg",
            preview=False,
        )
        result = client.purchase(prepared, preview=False)
        headers = {key.lower(): value for key, value in opener.last_request.header_items()}
        payload = json.loads(opener.last_request.data.decode("utf-8"))

        self.assertIn("idempotency-key", headers)
        self.assertEqual(headers["authorization"], "Bearer live-key")
        self.assertFalse(payload["test"])
        self.assertEqual(result["tileUrl"], "https://example.com/tile")
        self.assertEqual(result["projectDetails"][0]["name"], "Biochar")

    def test_simulate_client_does_not_build_or_use_network_opener(self) -> None:
        with mock.patch(
            "climate_plugin.providers.urllib.request.build_opener",
            side_effect=AssertionError("network opener should not be used"),
        ):
            client = create_ecologi_client(api_key=SIMULATE_API_KEY)
            prepared = prepare_ecologi_request(
                action=ACTION_TREE,
                quantity="1",
                preview=True,
            )
            result = client.purchase(prepared, preview=True)

        self.assertAlmostEqual(result["amount"], 0.8)
        self.assertEqual(result["currency"], "USD")

    def test_simulate_tree_price_uses_fixed_usd_example_rate(self) -> None:
        client = create_ecologi_client(api_key=SIMULATE_API_KEY)
        prepared = prepare_ecologi_request(
            action=ACTION_TREE,
            quantity="1",
            preview=True,
        )
        result = client.purchase(prepared, preview=True)

        self.assertAlmostEqual(result["amount"], 0.8)
        self.assertEqual(result["currency"], "USD")

    def test_simulate_avoidance_price_supports_kg_and_tonnes(self) -> None:
        client = create_ecologi_client(api_key=SIMULATE_API_KEY)

        kg_prepared = prepare_ecologi_request(
            action=ACTION_AVOIDANCE,
            quantity="100",
            units="kg",
            preview=True,
        )
        tonnes_prepared = prepare_ecologi_request(
            action=ACTION_AVOIDANCE,
            quantity="2",
            units="tonnes",
            preview=True,
        )

        kg_result = client.purchase(kg_prepared, preview=True)
        tonnes_result = client.purchase(tonnes_prepared, preview=True)

        self.assertAlmostEqual(kg_result["amount"], 1.25)
        self.assertEqual(kg_result["currency"], "USD")
        self.assertAlmostEqual(tonnes_result["amount"], 25.0)
        self.assertEqual(tonnes_result["currency"], "USD")

    def test_simulate_removal_price_uses_fixed_usd_per_kg_rate(self) -> None:
        client = create_ecologi_client(api_key=SIMULATE_API_KEY)
        prepared = prepare_ecologi_request(
            action=ACTION_REMOVAL,
            quantity="50",
            units="kg",
            preview=True,
        )
        result = client.purchase(prepared, preview=True)

        self.assertAlmostEqual(result["amount"], 14.0)
        self.assertEqual(result["currency"], "USD")

    def test_simulate_live_response_includes_idempotency_key(self) -> None:
        client = create_ecologi_client(api_key=SIMULATE_API_KEY)
        prepared = prepare_ecologi_request(
            action=ACTION_TREE,
            quantity="2",
            preview=False,
        )
        result = client.purchase(prepared, preview=False)

        self.assertEqual(result["amount"], 1.6)
        self.assertEqual(result["currency"], "USD")
        self.assertIn("idempotencyKey", result)
        self.assertEqual(
            result["treeUrl"],
            "https://ecologi.com/test?tree=604a74856345f7001caff578",
        )
        self.assertEqual(
            result["projectDetails"][0]["projectUrl"],
            "https://ecologi.com/projects/forest-restoration-in-kenya",
        )
        self.assertNotIn("simulated", result)

    def test_simulate_live_removal_includes_tile_url(self) -> None:
        client = create_ecologi_client(api_key=SIMULATE_API_KEY)
        prepared = prepare_ecologi_request(
            action=ACTION_REMOVAL,
            quantity="10",
            units="kg",
            preview=False,
        )
        result = client.purchase(prepared, preview=False)

        self.assertEqual(
            result["tileUrl"],
            "https://ecologi.com/test?tileId=604a74856345f7001caff578",
        )
        self.assertEqual(
            result["projectDetails"][0]["projectUrl"],
            "https://ecologi.com/projects/biochar-carbon-removal",
        )

    def test_simulate_live_avoidance_includes_project_details(self) -> None:
        client = create_ecologi_client(api_key=SIMULATE_API_KEY)
        prepared = prepare_ecologi_request(
            action=ACTION_AVOIDANCE,
            quantity="100",
            units="kg",
            preview=False,
        )
        result = client.purchase(prepared, preview=False)

        self.assertEqual(
            result["projectDetails"][0]["projectUrl"],
            "https://ecologi.com/projects/peatland-restoration-in-indonesia",
        )


if __name__ == "__main__":
    unittest.main()
