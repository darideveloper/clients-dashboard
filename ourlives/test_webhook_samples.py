"""End-to-end regression test driving the REAL n8n sample payloads (OL-8x/9x).

These files (`ourlives/docs/formidable-sample-data/OL-*.json`) are the actual
n8n webhook payloads used to develop the integration, so this test proves the
webhook handles real production data, not just hand-written fixtures.
"""

import glob
import json
import os

from django.core.management import call_command
from django.test import Client, TestCase

from ourlives.models import AppSettings, FormWebhookEvent, Order

SECRET = "verify-secret"

SAMPLES = sorted(
    os.path.basename(p)[: -len(".json")]
    for p in glob.glob("ourlives/docs/formidable-sample-data/OL-*.json")
)


def _number_of(name):
    return f"OL - {name.split('OL-')[1]}"


class SampleReplayTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        call_command("base_loaddata")
        settings = AppSettings.get_solo()
        settings.form_webhook_token = SECRET
        settings.save()

    def setUp(self):
        self.client = Client()

    def _post(self, body):
        return self.client.post(
            "/webhooks/ourlens/",
            data=json.dumps(body),
            content_type="application/json",
        )

    def _load(self, name):
        raw = json.load(open(f"ourlives/docs/formidable-sample-data/{name}.json"))
        item = raw[0] if isinstance(raw, list) else raw
        body = dict(item["body"])
        body["token"] = SECRET
        body["executionMode"] = item.get("executionMode", "")
        body["webhookUrl"] = item.get("webhookUrl", "")
        return body

    def _order(self, name):
        return Order.objects.get(order_number=_number_of(name))

    def test_replay_all_production_samples(self):
        for name in SAMPLES:
            if name == "OL-85":  # legacy raw-field-ID format, out of scope
                continue
            resp = self._post(self._load(name))
            self.assertEqual(resp.status_code, 200, name)

    def test_order_89_code_gap_preserved(self):
        self._post(self._load("OL-89"))
        order = self._order("OL-89")
        seqs = list(order.invitation_codes.order_by("sequence").values_list("sequence", flat=True))
        self.assertEqual(seqs, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19, 20])
        self.assertEqual(order.tokens_used, 19)
        for code in order.invitation_codes.select_related("project", "code_type"):
            self.assertEqual(code.max_use, 1)
            self.assertEqual(code.current_use, 0)
            self.assertTrue(code.is_active)
            self.assertEqual(code.project.name, "ourlens")
            self.assertEqual(code.code_type.code, "up_to_20")

    def test_order_93_five_up_to5_codes(self):
        self._post(self._load("OL-93"))
        order = self._order("OL-93")
        self.assertEqual(order.invitation_codes.count(), 5)
        self.assertTrue(all(c.code_type.code == "up_to_5" for c in order.invitation_codes.all()))

    def test_pilot_items_by_region(self):
        expectations = [
            ("OL-90", "USD", "US Regional Pilot"),
            ("OL-91", "CAD", "Canada Enterprise Pilot"),
            ("OL-92", "GBP", "UK Micro Pilot"),
            ("OL-93", "ZAR", "South Africa Regional Pilot"),
        ]
        for name, currency, product in expectations:
            self._post(self._load(name))
            order = self._order(name)
            self.assertTrue(order.is_pilot_order)
            self.assertEqual(order.pilot_currency.code, currency)
            self.assertIsNone(order.number_of_scans)
            item = order.items.get()
            self.assertEqual(item.product.name, product)
            self.assertEqual(item.quantity, 1)

    def test_non_pilot_sets_currency_scans_cost(self):
        self._post(self._load("OL-86"))
        order = self._order("OL-86")
        self.assertFalse(order.is_pilot_order)
        self.assertEqual(order.currency.code, "USD")
        self.assertEqual(order.number_of_scans, 11)
        self.assertEqual(order.cost_per_scan, 101)

    def test_execution_mode_recorded(self):
        self._post(self._load("OL-86"))
        event = FormWebhookEvent.objects.get(order__order_number=_number_of("OL-86"))
        self.assertEqual(event.execution_mode, "production")

    def test_repost_is_idempotent(self):
        self._post(self._load("OL-89"))
        order = self._order("OL-89")
        before = (order.invitation_codes.count(), order.tokens_used)
        resp = self._post(self._load("OL-89"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            Order.objects.filter(order_number=_number_of("OL-89")).count(), 1,
            "repost must not duplicate order",
        )
        order.refresh_from_db()
        self.assertEqual((order.invitation_codes.count(), order.tokens_used), before)

    def test_two_orders_share_same_company(self):
        self._post(self._load("OL-88"))
        self._post(self._load("OL-94"))
        org_88 = Order.objects.get(order_number=_number_of("OL-88")).organization
        org_94 = Order.objects.get(order_number=_number_of("OL-94")).organization
        self.assertEqual(org_88.pk, org_94.pk)
        self.assertEqual(org_88.orders.count(), 2)

    def test_legacy_ol85_rejected_creates_no_order(self):
        resp = self._post(self._load("OL-85"))
        # out of scope (design non-goal): tolerated as 200 `rejected`, no order
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Order.objects.filter(order_number__icontains="OL - 85").exists())
        event = FormWebhookEvent.objects.latest("id")
        self.assertEqual(event.status, "rejected")

    def test_duplicate_code_values_not_partial(self):
        # 5 identical code values -> exactly 1 deterministic code, logged, no error
        from ourlives.models import InvitationCode

        body = self._load("OL-86")
        body["mapping"]["code-1"] = "DUP-1"
        body["mapping"]["code-2"] = "DUP-1"
        body["mapping"]["code-3"] = "DUP-1"
        resp = self._post(body)
        self.assertEqual(resp.status_code, 200)
        order = Order.objects.get(order_number=_number_of("OL-86"))
        self.assertEqual(order.invitation_codes.count(), 1)
        self.assertEqual(order.tokens_used, 1)
        self.assertEqual(order.invitation_codes.get().code, "DUP-1")