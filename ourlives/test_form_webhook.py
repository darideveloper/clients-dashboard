import json
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase
from django.test.utils import override_settings
from django.urls import reverse

from ourlives.ingestion import (
    get_or_create_contact,
    get_or_create_org,
    get_or_create_rep,
    ingest,
    normalize_name,
    normalize_order_number,
    resolve_country,
    split_address,
    split_full_name,
)
from ourlives.models import (
    AppSettings,
    CodeType,
    Contact,
    ContactType,
    Country,
    Currency,
    FormWebhookEvent,
    InvitationCode,
    Order,
    OrderItem,
    OrderType,
    Organization,
    Product,
    Project,
)

CODETYPES = {
    "up_to_5": ("Up to 5 Additional Codes", 5),
    "up_to_20": ("Up to 20 Additional Codes", 20),
}


class WebhookFixtures(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project, _ = Project.objects.get_or_create(name="ourlens")
        cls.usd, _ = Currency.objects.get_or_create(
            code="USD", defaults={"name": "US Dollar", "exchange_rate": Decimal("1")}
        )
        cls.cad, _ = Currency.objects.get_or_create(
            code="CAD", defaults={"name": "Canadian Dollar", "exchange_rate": Decimal("1")}
        )
        cls.gbp, _ = Currency.objects.get_or_create(
            code="GBP", defaults={"name": "British Pound", "exchange_rate": Decimal("1")}
        )
        cls.zar, _ = Currency.objects.get_or_create(
            code="ZAR", defaults={"name": "South African Rand", "exchange_rate": Decimal("1")}
        )
        cls.eur, _ = Currency.objects.get_or_create(
            code="EUR", defaults={"name": "Euro", "exchange_rate": Decimal("1")}
        )
        cls.product_cad = Product.objects.get_or_create(
            name="Canada Enterprise Pilot",
            defaults={"currency": cls.cad, "tier": "enterprise", "unit_price": Decimal("17995")},
        )[0]
        cls.product_uk = Product.objects.get_or_create(
            name="UK Micro Pilot",
            defaults={"currency": cls.gbp, "tier": "micro", "unit_price": Decimal("995")},
        )[0]
        Product.objects.get_or_create(
            name="US Micro Pilot",
            defaults={"currency": cls.usd, "tier": "micro", "unit_price": Decimal("0")},
        )
        Product.objects.get_or_create(
            name="South Africa Regional Pilot",
            defaults={"currency": cls.zar, "tier": "regional", "unit_price": Decimal("0")},
        )
        for code, (name, max_codes) in CODETYPES.items():
            CodeType.objects.get_or_create(
                name=name, defaults={"code": code, "max_codes": max_codes}
            )
        for code, name in (("pilot", "Pilot Order"), ("standard", "Standard Order")):
            OrderType.objects.get_or_create(name=name, defaults={"code": code})
        for code, name in (("primary", "Primary Contact"), ("invoice", "Invoice Contact")):
            ContactType.objects.get_or_create(name=name, defaults={"code": code})
        cls.sweden, _ = Country.objects.get_or_create(
            name="Sweden",
            defaults={"iso2": "SE", "iso3": "SWE"},
        )
        Country.objects.get_or_create(
            name="Holy See", defaults={"iso2": "VA", "iso3": "VAT"}
        )
        AppSettings.get_solo()

    def payload(self, mapping, token="secret-token", execution_mode="production"):
        return {
            "token": token,
            "event": "create",
            "mapping": mapping,
            "webhookUrl": "https://n8n.example/webhook/abc",
            "executionMode": execution_mode,
        }

    def mapping(self, overrides=None):
        overrides = overrides or {}
        base = {
            "order-number": "OL - 95",
            "is-this-a-pilot-order": "No",
            "is-this-an-upgrade-from-a-pilot": "No",
            "is-this-an-order-following-a-referral": "No",
            "name-of-the-organsation-who-is-referring": "",
            "you-have-selected-yes-to-an-upgrade-from-a-pilot": "",
            "reps-name": "John Doe",
            "reps-email": "john@example.com",
            "company-address-purchasing-ourlens-scans": (
                "123 Main St, Suite 2, Springfield, IL, 62704, Sweden"
            ),
            "primary-contact": "Jane Smith",
            "primary-contact-email": "jane@example.com",
            "primary-contact-phone": "5551234",
            "invoice-contact": "Jack Smith",
            "invoice-email": "jack@example.com",
            "invoice-contact-phone": "5555678",
            "pilot-currency": "",
            "currency": "USD",
            "po-number": "PO-1",
            "number-of-scans": "100",
            "cost-per-scan": "2.50",
            "total-agreed-price": "9999",
            "product-us": "",
            "quantity-us": "",
            "us-dollars": "",
            "product-canada": "",
            "quantity-canada": "",
            "canadian-dollars": "",
            "product-uk": "",
            "quantity-uk": "",
            "gbp": "",
            "product-south-africa": "",
            "quantity-south-africa": "",
            "zar": "",
            "i-would-like-additional-codes": "No",
            "how-many-additional-codes-do-you-require": "",
            **{f"code-{n}": "" for n in range(1, 21)},
            "please-add-an-additional-information-relating-to-this-order": "",
        }
        base.update(overrides)
        return base


class HelperTests(WebhookFixtures):
    def test_normalize_order_number(self):
        self.assertEqual(normalize_order_number("OL - 95"), "OL-95")
        self.assertEqual(normalize_order_number("OL-95"), "OL-95")
        self.assertEqual(normalize_order_number(" OL -  95 "), "OL-95")

    def test_normalize_name(self):
        self.assertEqual(normalize_name("  Acme   Health  "), "acmehealth")

    def test_split_full_name(self):
        self.assertEqual(split_full_name("Demo Harry Judd"), ("Demo", "Harry Judd"))
        self.assertEqual(split_full_name("Solo"), ("Solo", ""))

    def test_split_address_six_part(self):
        parsed = split_address("123 Main St, Suite 2, Springfield, IL, 62704, Sweden")
        self.assertEqual(parsed["line1"], "123 Main St")
        self.assertEqual(parsed["line2"], "Suite 2")
        self.assertEqual(parsed["city"], "Springfield")
        self.assertEqual(parsed["state"], "IL")
        self.assertEqual(parsed["zip"], "62704")
        self.assertEqual(parsed["country"], "Sweden")

    def test_split_address_five_part(self):
        parsed = split_address("123 Main St, Springfield, IL, 62704, Sweden")
        self.assertEqual(parsed["line1"], "123 Main St")
        self.assertEqual(parsed["line2"], "")
        self.assertEqual(parsed["city"], "Springfield")

    def test_split_address_blank(self):
        parsed = split_address("")
        self.assertEqual(parsed["line1"], "")


class MatchOrCreateTests(WebhookFixtures):
    def test_org_created_then_reused_by_normalized_line1(self):
        org = get_or_create_org("123 Main St")
        again = get_or_create_org("123  MAIN St")
        self.assertEqual(org.pk, again.pk)
        self.assertEqual(Organization.objects.filter(name="123 Main St").count(), 1)

    def test_rep_created_then_reused_by_email(self):
        rep = get_or_create_rep("john@example.com", "John Doe")
        again = get_or_create_rep("JOHN@example.com", "Johnny Doe")
        self.assertEqual(rep.pk, again.pk)
        self.assertEqual(rep.first_name, "John")
        self.assertEqual(rep.last_name, "Doe")

    def test_contact_created_then_reused_within_org(self):
        primary = ContactType.objects.get(code="primary")
        org = Organization.objects.create(name="Acme")
        contact = get_or_create_contact(org, "jane@example.com", "Jane Smith", "555", primary)
        again = get_or_create_contact(org, "JANE@example.com", "Janet", "555", primary)
        self.assertEqual(contact.pk, again.pk)


class CountryTests(WebhookFixtures):
    def test_alias_resolves(self):
        country = resolve_country("Vatican City")
        self.assertIsNotNone(country)
        self.assertEqual(country.name, "Holy See")

    def test_nullable_fallback(self):
        self.assertIsNone(resolve_country("Kosovo"))


class EndpointTests(WebhookFixtures):
    def setUp(self):
        super().setUp()
        AppSettings.objects.filter(pk=AppSettings.get_solo().pk).update(
            form_webhook_token="secret-token"
        )
        self.client = Client()

    def post(self, body, content_type="application/json"):
        return self.client.post(
            "/webhooks/ourlens/",
            data=json.dumps(body),
            content_type=content_type,
        )

    def test_200_production_creates_order_and_audit(self):
        resp = self.post(self.payload(self.mapping()))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.get()
        self.assertEqual(order.order_number, "OL - 95")
        event = FormWebhookEvent.objects.get()
        self.assertEqual(event.status, "created")
        self.assertEqual(event.execution_mode, "production")

    def test_200_test_mode_creates_and_records_mode(self):
        body = self.payload(self.mapping(), execution_mode="test")
        resp = self.post(body)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(FormWebhookEvent.objects.get().execution_mode, "test")
        self.assertEqual(Order.objects.count(), 1)

    def test_403_bad_token(self):
        resp = self.post(self.payload(self.mapping(), token="wrong"))
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(FormWebhookEvent.objects.get().status, "rejected")
        self.assertEqual(Order.objects.count(), 0)

    def test_400_wrong_content_type(self):
        resp = self.post(self.payload(self.mapping()), content_type="text/plain")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Order.objects.count(), 0)

    def test_400_invalid_json(self):
        resp = self.client.post("/webhooks/ourlens/", data="{not json", content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_empty_mapping_rejected_returns_200(self):
        resp = self.post({"token": "secret-token", "mapping": {}})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(FormWebhookEvent.objects.get().status, "rejected")

    def test_duplicate_order_reconciles_no_duplicate(self):
        self.post(self.payload(self.mapping()))
        resp = self.post(self.payload(self.mapping()))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(FormWebhookEvent.objects.filter(status="updated").count(), 1)


class InvitationCodeTests(WebhookFixtures):
    def make(self, mapping):
        return ingest(mapping)

    def test_auto_creation_with_gap(self):
        mapping = self.mapping({
            "i-would-like-additional-codes": "Yes",
            "how-many-additional-codes-do-you-require": "Up to 20 Additional Codes",
            "code-14": "P04-015",
            "code-16": "P04-016",
            "code-17": "P04-017",
        })
        status, order = self.make(mapping)
        self.assertEqual(status, "created")
        codes = order.invitation_codes.order_by("sequence")
        self.assertEqual(list(codes.values_list("sequence", flat=True)), [14, 16, 17])
        for code in codes:
            self.assertEqual(code.max_use, 1)
            self.assertEqual(code.current_use, 0)
            self.assertEqual(code.is_active, True)
            self.assertEqual(code.project.name, "ourlens")
        self.assertEqual(order.tokens_used, 3)

    def test_code_type_null_when_no_bundle(self):
        mapping = self.mapping({"code-1": "ABC-1"})
        status, order = self.make(mapping)
        self.assertEqual(order.invitation_codes.get().code_type, None)

    def test_add_only_reconcile_preserves_codes(self):
        status, order = self.make(self.mapping({"code-1": "K1"}))
        first = order.invitation_codes.get()
        status, order = self.make(
            self.mapping({"order-number": "OL-95", "code-1": "K1", "code-2": "K2"})
        )
        order.refresh_from_db()
        self.assertEqual(order.invitation_codes.count(), 2)
        self.assertEqual(order.invitation_codes.get(code="K1").pk, first.pk)
        self.assertEqual(order.tokens_used, 2)

    def test_creation_succeeds_when_pool_exhausted(self):
        AppSettings.objects.filter(pk=AppSettings.get_solo().pk).update(total_tokens=0)
        mapping = self.mapping({"code-1": "X1", "code-2": "X2"})
        status, order = self.make(mapping)
        self.assertEqual(status, "created")
        self.assertEqual(order.invitation_codes.count(), 2)


class PilotOrderTests(WebhookFixtures):
    def test_pilot_item_built_by_region(self):
        mapping = self.mapping({
            "is-this-a-pilot-order": "Yes",
            "pilot-currency": "CAD",
            "product-canada": "Enterprise Pilot",
            "quantity-canada": "1",
            "canadian-dollars": "17995"})
        status, order = ingest(mapping)
        self.assertEqual(status, "created")
        self.assertTrue(order.is_pilot_order)
        self.assertEqual(order.pilot_currency.code, "CAD")
        self.assertIsNone(order.number_of_scans)
        item = order.items.get()
        self.assertEqual(item.product.name, "Canada Enterprise Pilot")
        self.assertEqual(item.quantity, 1)
        self.assertEqual(item.unit_price, Decimal("17995"))
        self.assertEqual(order.invitation_codes.count(), 0)

    def test_non_pilot_sets_scans_cost(self):
        status, order = ingest(self.mapping())
        self.assertFalse(order.is_pilot_order)
        self.assertEqual(order.currency.code, "USD")
        self.assertEqual(order.number_of_scans, 100)
        self.assertEqual(order.cost_per_scan, Decimal("2.50"))
        self.assertEqual(order.items.count(), 0)

    def test_blank_pilot_radio_defaults_standard(self):
        mapping = self.mapping({"is-this-a-pilot-order": ""})
        status, order = ingest(mapping)
        self.assertFalse(order.is_pilot_order)

    def test_upgrade_yes_pilot_no_is_standard_with_flag(self):
        mapping = self.mapping({
            "is-this-a-pilot-order": "No",
            "is-this-an-upgrade-from-a-pilot": "Yes"})
        status, order = ingest(mapping)
        self.assertFalse(order.is_pilot_order)
        self.assertTrue(order.is_upgrade_from_pilot)

    def test_eur_pilot_creates_zero_price_and_flags(self):
        mapping = self.mapping({
            "is-this-a-pilot-order": "Yes",
            "pilot-currency": "EUR"})
        status, order = ingest(mapping)
        self.assertEqual(status, "created")
        self.assertEqual(order.items.count(), 0)
        self.assertEqual(order.number_of_scans, None)

    def test_total_agreed_price_ignored_for_scans(self):
        status, order = ingest(self.mapping())
        self.assertEqual(order.total_agreed_price, Decimal("250.00"))


class BaseLoaddataTests(TestCase):
    def test_base_loaddata_creates_ourlens_project(self):
        call_command("base_loaddata")
        self.assertTrue(Project.objects.filter(name="ourlens").exists())


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class AdminTests(WebhookFixtures):
    def setUp(self):
        super().setUp()
        AppSettings.objects.filter(pk=AppSettings.get_solo().pk).update(
            form_webhook_token="secret-token"
        )
        self.user = User.objects.create_superuser("admin", "admin@example.com", "x")
        self.client = Client()
        self.client.force_login(self.user)

    def test_form_webhook_event_read_only(self):
        from ourlives.admin import FormWebhookEventAdmin

        admin = FormWebhookEventAdmin(FormWebhookEvent, None)
        self.assertFalse(admin.has_add_permission(None))
        self.assertFalse(admin.has_change_permission(None))
        self.assertFalse(admin.has_delete_permission(None))

    def test_appsettings_token_field_visible(self):
        url = reverse("admin:ourlives_appsettings_change")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "form_webhook_token")

    def test_order_exposes_tokens_used(self):
        status, order = ingest(self.mapping_with_codes())
        url = reverse("admin:ourlives_order_change", args=[order.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, ">Tokens used</label>")

    def mapping_with_codes(self):
        return self.mapping({"code-1": "T-1", "code-2": "T-2"})