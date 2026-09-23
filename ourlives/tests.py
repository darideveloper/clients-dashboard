import json
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.test import TestCase, Client, override_settings
from django.urls import reverse

from ourlives.models import (
    AppSettings,
    CodeType,
    Contact,
    ContactType,
    Country,
    Currency,
    InvitationCode,
    Order,
    OrderItem,
    OrderType,
    Organization,
    OrganizationAddress,
    Product,
    Project,
    Rep,
    StripeEvent,
    UNCATEGORIZED_CURRENCY,
    attach_money_breakdowns,
    calculate_token_count,
    format_currency_breakdown,
)


class ProjectTests(TestCase):
    def test_create_project(self):
        project = Project.objects.create(name="Launch Alpha", description="First batch")
        self.assertEqual(project.name, "Launch Alpha")
        self.assertEqual(project.description, "First batch")
        self.assertEqual(str(project), "Launch Alpha")

    def test_duplicate_project_name_raises_error(self):
        Project.objects.create(name="Launch Alpha")
        with self.assertRaises(IntegrityError):
            Project.objects.create(name="Launch Alpha")


class OrganizationTests(TestCase):
    def test_create_organization(self):
        org = Organization.objects.create(name="Acme Corp", description="Billing entity")
        self.assertEqual(org.name, "Acme Corp")
        self.assertEqual(org.description, "Billing entity")
        self.assertEqual(str(org), "Acme Corp")

    def test_duplicate_organization_name_raises_error(self):
        Organization.objects.create(name="Acme Corp")
        with self.assertRaises(IntegrityError):
            Organization.objects.create(name="Acme Corp")


class InvitationCodeBaseTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.organization = Organization.objects.create(name="Test Org")
        AppSettings.get_solo()
        AppSettings.objects.update(total_tokens=100)


class InvitationCodeCreationTests(InvitationCodeBaseTestCase):
    def test_create_invitation_code_with_auto_generated_code(self):
        code = InvitationCode.objects.create(project=self.project, organization=self.organization, max_use=10)
        self.assertIsNotNone(code.code)
        self.assertNotEqual(code.code, "")
        self.assertTrue(code.is_active)
        self.assertEqual(code.current_use, 0)
        self.assertEqual(code.max_use, 10)
        self.assertEqual(str(code), code.code)

    def test_create_code_within_pool_limit(self):
        code = InvitationCode.objects.create(project=self.project, organization=self.organization, max_use=10)
        self.assertIsNotNone(code.pk)

    def test_create_code_exceeding_pool_limit(self):
        InvitationCode.objects.create(project=self.project, organization=self.organization, max_use=100)
        with self.assertRaises(ValidationError):
            InvitationCode.objects.create(project=self.project, organization=self.organization, max_use=1)

    def test_protect_organization_with_active_codes(self):
        org = Organization.objects.create(name="Protected Org")
        InvitationCode.objects.create(project=self.project, organization=org, max_use=5)
        with self.assertRaises(ProtectedError):
            org.delete()


class InvitationCodeUpdateTests(InvitationCodeBaseTestCase):
    def setUp(self):
        super().setUp()
        self.code = InvitationCode.objects.create(
            project=self.project, organization=self.organization, max_use=10, current_use=3,
        )

    def test_update_increasing_max_use_within_limit(self):
        self.code.max_use = 15
        self.code.save()
        self.code.refresh_from_db()
        self.assertEqual(self.code.max_use, 15)

    def test_update_increasing_max_use_beyond_limit(self):
        other = Project.objects.create(name="Other")
        InvitationCode.objects.create(project=other, organization=self.organization, max_use=90)
        self.code.max_use = 11
        with self.assertRaises(ValidationError):
            self.code.save()

    def test_reject_max_use_reduction_below_current_use(self):
        self.code.max_use = 2
        with self.assertRaises(ValidationError):
            self.code.save()

    def test_deactivated_code_tokens_remain_consumed(self):
        self.code.is_active = False
        self.code.save()
        assigned = AppSettings.get_solo().tokens_assigned
        self.assertEqual(assigned, 10)

    def test_reactivation_succeeds(self):
        self.code.is_active = False
        self.code.save()
        self.code.is_active = True
        self.code.save()
        self.code.refresh_from_db()
        self.assertTrue(self.code.is_active)

    def test_reactivation_with_increased_use_rejected_when_pool_full(self):
        other = Project.objects.create(name="Other")
        self.code.max_use = 3
        self.code.save()
        InvitationCode.objects.create(project=other, organization=self.organization, max_use=97)
        self.code.max_use = 10
        self.code.is_active = True
        with self.assertRaises(ValidationError):
            self.code.save()


class AppSettingsTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Test Org")
        AppSettings.get_solo()
        AppSettings.objects.update(total_tokens=100)

    def test_computed_properties(self):
        project = Project.objects.create(name="Test")
        InvitationCode.objects.create(project=project, organization=self.organization, max_use=5, current_use=3)
        InvitationCode.objects.create(project=project, organization=self.organization, max_use=5, current_use=3)
        InvitationCode.objects.create(project=project, organization=self.organization, max_use=10, current_use=0)

        settings = AppSettings.get_solo()
        self.assertEqual(settings.tokens_assigned, 20)
        self.assertEqual(settings.tokens_used, 6)
        self.assertEqual(settings.tokens_available, 80)

    def test_get_solo_returns_same_instance(self):
        a = AppSettings.get_solo()
        b = AppSettings.get_solo()
        self.assertEqual(a.pk, b.pk)

    def test_str(self):
        settings = AppSettings.get_solo()
        self.assertEqual(str(settings), "App Settings")

    def test_reduce_total_tokens_below_assigned_via_update_succeeds(self):
        """AppSettings.objects.update() bypasses save() validation."""
        project = Project.objects.create(name="Test")
        InvitationCode.objects.create(project=project, organization=self.organization, max_use=80)
        self.assertEqual(AppSettings.get_solo().tokens_assigned, 80)
        AppSettings.objects.update(total_tokens=50)
        settings = AppSettings.get_solo()
        self.assertEqual(settings.total_tokens, 50)
        with self.assertRaises(ValidationError):
            InvitationCode.objects.create(project=project, organization=self.organization, max_use=1)

    def test_reduce_total_tokens_below_assigned_via_save_raises_error(self):
        project = Project.objects.create(name="Test")
        InvitationCode.objects.create(project=project, organization=self.organization, max_use=80)
        self.assertEqual(AppSettings.get_solo().tokens_assigned, 80)
        settings = AppSettings.get_solo()
        settings.total_tokens = 50
        with self.assertRaises(ValidationError):
            settings.save()


from decimal import Decimal as D


class AppSettingsPricingValidationTests(TestCase):
    def setUp(self):
        self.settings = AppSettings.get_solo()

    def test_rejects_negative_price_per_token(self):
        self.settings.price_per_token = D("-1")
        with self.assertRaises(ValidationError):
            self.settings.save()

    def test_rejects_negative_min_purchase_amount(self):
        self.settings.min_purchase_amount = D("-5")
        with self.assertRaises(ValidationError):
            self.settings.save()

    def test_allows_zero_price_per_token(self):
        self.settings.price_per_token = D("0")
        self.settings.min_purchase_amount = D("0")
        try:
            self.settings.save()
        except ValidationError:
            self.fail("Zero price_per_token should be allowed")

    def test_allows_zero_min_purchase_amount(self):
        self.settings.price_per_token = D("0.10")
        self.settings.min_purchase_amount = D("0")
        try:
            self.settings.save()
        except ValidationError:
            self.fail("Zero min_purchase_amount should be allowed")

    def test_allows_valid_pricing(self):
        self.settings.price_per_token = D("0.50")
        self.settings.min_purchase_amount = D("5.00")
        try:
            self.settings.save()
        except ValidationError:
            self.fail("Valid pricing should be allowed")


class CalculateTokenCountTests(TestCase):
    def test_exact_division(self):
        self.assertEqual(calculate_token_count(D("10.00"), D("0.10")), 100)

    def test_non_exact_division(self):
        self.assertEqual(calculate_token_count(D("5.00"), D("0.30")), 16)

    def test_amount_below_price_returns_zero(self):
        self.assertEqual(calculate_token_count(D("1.00"), D("1.50")), 0)

    def test_zero_price_returns_zero(self):
        self.assertEqual(calculate_token_count(D("10.00"), D("0")), 0)

    def test_large_amount(self):
        self.assertEqual(calculate_token_count(D("1000.00"), D("0.05")), 20000)


class CanPurchaseTests(TestCase):
    def setUp(self):
        self.client = Client()

    def _create_admin_user(self):
        user = User.objects.create_superuser("admin", "admin@test.com", "password")
        return user

    def _create_staff_user(self, permissions=None):
        user = User.objects.create_user("staff", "staff@test.com", "password", is_staff=True)
        if permissions:
            for perm in permissions:
                app_label, codename = perm.split(".")
                user.user_permissions.add(
                    Permission.objects.get(content_type__app_label=app_label, codename=codename)
                )
        return user

    def test_admin_user_can_purchase(self):
        from ourlives.admin import can_purchase
        user = self._create_admin_user()
        request = type("Request", (), {"user": user, "is_staff": True})()
        self.assertTrue(can_purchase(request))

    def test_ourlives_staff_user_can_purchase(self):
        from ourlives.admin import can_purchase
        user = self._create_staff_user(["ourlives.view_project"])
        request = type("Request", (), {"user": user, "is_staff": True})()
        self.assertTrue(can_purchase(request))

    def test_non_ourlives_staff_cannot_purchase(self):
        from ourlives.admin import can_purchase
        user = self._create_staff_user([])
        request = type("Request", (), {"user": user, "is_staff": True})()
        self.assertFalse(can_purchase(request))

    def test_non_staff_user_cannot_purchase(self):
        from ourlives.admin import can_purchase
        user = User.objects.create_user("regular", "regular@test.com", "password")
        request = type("Request", (), {"user": user, "is_staff": False})()
        self.assertFalse(can_purchase(request))


class CreateCheckoutSessionTests(TestCase):
    @patch("ourlives.stripe.stripe.checkout.Session.create")
    def test_create_checkout_session_correct_params(self, mock_create):
        mock_create.return_value = type("Session", (), {"url": "https://checkout.stripe.com/test"})()

        from ourlives.stripe import create_checkout_session

        url = create_checkout_session(
            unit_amount_cents=10,
            quantity=20,
            app_settings_id=1,
            success_url="https://example.com/admin/ourlives/appsettings/purchase/",
            cancel_url="https://example.com/admin/ourlives/appsettings/purchase/",
            customer_email="test@example.com",
        )

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]

        self.assertEqual(call_kwargs["payment_method_types"], [])
        self.assertEqual(call_kwargs["customer_email"], "test@example.com")
        self.assertEqual(call_kwargs["adaptive_pricing"], {"enabled": True})

        line_items = call_kwargs["line_items"]
        self.assertEqual(line_items[0]["price_data"]["currency"], "usd")
        self.assertEqual(line_items[0]["price_data"]["unit_amount"], 10)
        self.assertEqual(line_items[0]["price_data"]["product_data"]["name"], "Invitation Code Tokens")
        self.assertEqual(line_items[0]["quantity"], 20)

        self.assertEqual(call_kwargs["metadata"]["source"], "ourlives")
        self.assertEqual(call_kwargs["metadata"]["token_count"], "20")
        self.assertEqual(call_kwargs["metadata"]["app_settings_id"], "1")
        self.assertIn("success_url", call_kwargs)
        self.assertIn("cancel_url", call_kwargs)
        self.assertIn("/admin/ourlives/appsettings/purchase/", call_kwargs["success_url"])
        self.assertIn("/admin/ourlives/appsettings/purchase/", call_kwargs["cancel_url"])
        self.assertEqual(url, "https://checkout.stripe.com/test")


import io
import tempfile

from django.core.management import call_command
from django.test.utils import override_settings


class ImportInvitationCodesTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="ourlens")
        self.organization = Organization.objects.create(name="Test Org")
        AppSettings.get_solo()
        AppSettings.objects.update(total_tokens=100)

    def _write_csv(self, lines):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="")
        f.write("code,is_active,max_use_rate,current_use_rate\n")
        f.writelines(lines)
        f.close()
        return f.name

    def test_happy_path_bulk_import(self):
        csv_path = self._write_csv([
            "ABC001,true,10,0\n",
            "ABC002,True,5,2\n",
        ])
        out = io.StringIO()
        call_command("import_invitation_codes", project="ourlens", organization="Test Org", csv=csv_path, stdout=out)
        self.assertIn("2 created", out.getvalue())
        self.assertEqual(InvitationCode.objects.count(), 2)

    def test_project_not_found(self):
        csv_path = self._write_csv(["X,true,5,0\n"])
        with self.assertRaisesMessage(Exception, "Project 'ghost' not found"):
            call_command("import_invitation_codes", project="ghost", organization="Test Org", csv=csv_path)

    def test_csv_file_not_found(self):
        with self.assertRaisesRegex(Exception, "CSV file not found"):
            call_command("import_invitation_codes", project="ourlens", organization="Test Org", csv="/no/such/file.csv")

    def test_missing_required_columns(self):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
        f.write("code,is_active\nX,true\n")
        f.close()
        with self.assertRaisesRegex(Exception, "missing required columns"):
            call_command("import_invitation_codes", project="ourlens", organization="Test Org", csv=f.name)

    def test_rejects_non_integer_max_use(self):
        csv_path = self._write_csv(["X,true,notanint,0\n"])
        with self.assertRaisesRegex(Exception, "invalid row"):
            call_command("import_invitation_codes", project="ourlens", organization="Test Org", csv=csv_path)

    def test_rejects_non_boolean_is_active(self):
        csv_path = self._write_csv(["X,banana,5,0\n"])
        with self.assertRaisesRegex(Exception, "invalid row"):
            call_command("import_invitation_codes", project="ourlens", organization="Test Org", csv=csv_path)

    def test_rejects_current_exceeds_max(self):
        csv_path = self._write_csv(["X,true,5,10\n"])
        with self.assertRaisesRegex(Exception, "invalid row"):
            call_command("import_invitation_codes", project="ourlens", organization="Test Org", csv=csv_path)

    def test_rejects_max_use_zero(self):
        csv_path = self._write_csv(["X,true,0,0\n"])
        with self.assertRaisesRegex(Exception, "invalid row"):
            call_command("import_invitation_codes", project="ourlens", organization="Test Org", csv=csv_path)

    def test_token_pool_auto_bump(self):
        AppSettings.objects.update(total_tokens=10)
        csv_path = self._write_csv([
            "A,true,10,0\n",
            "B,true,10,0\n",
        ])
        out = io.StringIO()
        call_command("import_invitation_codes", project="ourlens", organization="Test Org", csv=csv_path, stdout=out)
        self.assertIn("bumped", out.getvalue())
        self.assertEqual(AppSettings.get_solo().total_tokens, 20)

    def test_token_pool_sufficient_no_bump(self):
        AppSettings.objects.update(total_tokens=50)
        csv_path = self._write_csv(["A,true,10,0\n"])
        out = io.StringIO()
        call_command("import_invitation_codes", project="ourlens", organization="Test Org", csv=csv_path, stdout=out)
        self.assertIn("sufficient", out.getvalue())
        self.assertEqual(AppSettings.get_solo().total_tokens, 50)

    def test_idempotent_re_run_overwrites_existing(self):
        csv_path = self._write_csv(["A,true,10,0\n"])
        call_command("import_invitation_codes", project="ourlens", organization="Test Org", csv=csv_path)
        self.assertEqual(InvitationCode.objects.count(), 1)
        out = io.StringIO()
        call_command("import_invitation_codes", project="ourlens", organization="Test Org", csv=csv_path, stdout=out)
        self.assertIn("updated", out.getvalue())
        self.assertIn("1 updated", out.getvalue())
        self.assertEqual(InvitationCode.objects.count(), 1)

    def test_api_token_column_ignored(self):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="")
        f.write("code,is_active,max_use_rate,current_use_rate,api_token\n")
        f.write("A,true,5,0,sk-or-v1-abc123\n")
        f.close()
        out = io.StringIO()
        call_command("import_invitation_codes", project="ourlens", organization="Test Org", csv=f.name, stdout=out)
        self.assertIn("1 created", out.getvalue())
        self.assertEqual(InvitationCode.objects.count(), 1)

    def test_organization_not_found(self):
        csv_path = self._write_csv(["X,true,5,0\n"])
        with self.assertRaisesMessage(Exception, "Organization 'Ghost' not found"):
            call_command("import_invitation_codes", project="ourlens", organization="Ghost", csv=csv_path)

    def test_valid_organization_import(self):
        csv_path = self._write_csv(["CODE1,true,10,0\n"])
        out = io.StringIO()
        call_command("import_invitation_codes", project="ourlens", organization="Test Org", csv=csv_path, stdout=out)
        self.assertIn("1 created", out.getvalue())
        code = InvitationCode.objects.get(code="CODE1")
        self.assertEqual(code.organization, self.organization)


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class PurchaseViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.purchase_url = "/admin/ourlives/appsettings/purchase/"

    def _create_ourlives_user(self):
        user = User.objects.create_user("op", "op@test.com", "password", is_staff=True)
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="ourlives", codename="view_project")
        )
        return user

    def test_ourlives_user_gets_200(self):
        user = self._create_ourlives_user()
        self.client.force_login(user)
        response = self.client.get(self.purchase_url)
        self.assertEqual(response.status_code, 200)

    def test_non_ourlives_user_gets_403(self):
        user = User.objects.create_user("noop", "noop@test.com", "password", is_staff=True)
        self.client.force_login(user)
        response = self.client.get(self.purchase_url)
        self.assertEqual(response.status_code, 403)

    def test_unconfigured_pricing_shows_disabled_state(self):
        user = self._create_ourlives_user()
        self.client.force_login(user)
        settings = AppSettings.get_solo()
        settings.price_per_token = D("0")
        settings.min_purchase_amount = D("0")
        settings.stripe_price_id = ""
        settings.save()
        response = self.client.get(self.purchase_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Price not configured")

    def test_configured_pricing_shows_active_form(self):
        user = self._create_ourlives_user()
        self.client.force_login(user)
        settings = AppSettings.get_solo()
        settings.price_per_token = D("0.10")
        settings.min_purchase_amount = D("5.00")
        settings.stripe_price_id = "price_test_abc"
        settings.save()
        response = self.client.get(self.purchase_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Price per token")
        self.assertContains(response, "0.10")


class CreateCheckoutViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = "/stripe/create-checkout/"

    def _create_ourlives_user(self):
        user = User.objects.create_user("op", "op@test.com", "password", is_staff=True)
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="ourlives", codename="view_project")
        )
        return user

    def _configure_pricing(self):
        settings = AppSettings.get_solo()
        settings.price_per_token = D("0.10")
        settings.min_purchase_amount = D("5.00")
        settings.stripe_price_id = "price_test_abc"
        settings.save()

    def test_non_ourlives_user_gets_403(self):
        user = User.objects.create_user("noop", "noop@test.com", "password", is_staff=True)
        self.client.force_login(user)
        response = self.client.post(self.url, {"amount": "10.00"})
        self.assertEqual(response.status_code, 403)

    def test_rejects_amount_below_minimum(self):
        user = self._create_ourlives_user()
        self.client.force_login(user)
        self._configure_pricing()
        response = self.client.post(self.url, {"amount": "1.00"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_rejects_when_price_not_configured(self):
        user = self._create_ourlives_user()
        self.client.force_login(user)
        response = self.client.post(self.url, {"amount": "10.00"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Price must be configured first", response.json().get("error", ""))

    def test_rejects_amount_too_low_for_one_token(self):
        user = self._create_ourlives_user()
        self.client.force_login(user)
        settings = AppSettings.get_solo()
        settings.price_per_token = D("1.50")
        settings.min_purchase_amount = D("0")
        settings.stripe_price_id = "price_test_abc"
        settings.save()
        response = self.client.post(self.url, {"amount": "1.00"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Amount too low", response.json().get("error", ""))

    @patch("ourlives.stripe.stripe.checkout.Session.create")
    def test_successful_checkout_redirects(self, mock_create):
        mock_create.return_value = type("Session", (), {"url": "https://checkout.stripe.com/test"})()
        user = self._create_ourlives_user()
        self.client.force_login(user)
        self._configure_pricing()
        response = self.client.post(self.url, {"amount": "10.00"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://checkout.stripe.com/test")
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        self.assertEqual(call_kwargs["payment_method_types"], [])
        self.assertEqual(call_kwargs["customer_email"], "op@test.com")
        self.assertEqual(call_kwargs["adaptive_pricing"], {"enabled": True})
        line_items = call_kwargs["line_items"]
        self.assertEqual(line_items[0]["price_data"]["currency"], "usd")
        self.assertEqual(line_items[0]["price_data"]["unit_amount"], 10)
        self.assertEqual(line_items[0]["quantity"], 100)
        self.assertIn("/stripe/success/?token_count=100&session_id=", call_kwargs["success_url"])
        self.assertIn("/admin/ourlives/appsettings/purchase/", call_kwargs["cancel_url"])


class StripeEventModelTests(TestCase):
    def test_create_stripe_event_with_minimal_fields(self):
        event = StripeEvent.objects.create(
            stripe_event_id="evt_test_123",
            source="ourlives",
            token_count=100,
            amount_cents=1000,
        )
        self.assertEqual(event.stripe_event_id, "evt_test_123")
        self.assertEqual(event.source, "ourlives")
        self.assertEqual(event.token_count, 100)
        self.assertEqual(event.amount_cents, 1000)
        self.assertEqual(event.presentment_currency, "")
        self.assertIsNone(event.presentment_amount)

    def test_create_stripe_event_with_presentment_details(self):
        event = StripeEvent.objects.create(
            stripe_event_id="evt_test_456",
            source="ourlives",
            token_count=50,
            amount_cents=1000,
            presentment_currency="eur",
            presentment_amount=920,
        )
        self.assertEqual(event.presentment_currency, "eur")
        self.assertEqual(event.presentment_amount, 920)

    def test_presentment_fields_are_optional(self):
        event = StripeEvent.objects.create(
            stripe_event_id="evt_test_789",
            source="ourlives",
            token_count=25,
            amount_cents=500,
        )
        self.assertEqual(event.presentment_currency, "")
        self.assertIsNone(event.presentment_amount)

    def test_duplicate_stripe_event_id_raises_error(self):
        StripeEvent.objects.create(
            stripe_event_id="evt_test_123",
            source="ourlives",
            token_count=100,
            amount_cents=1000,
        )
        with self.assertRaises(IntegrityError):
            StripeEvent.objects.create(
                stripe_event_id="evt_test_123",
                source="ourlives",
                token_count=50,
                amount_cents=500,
            )

    def test_source_field_saves_correctly(self):
        event = StripeEvent.objects.create(
            stripe_event_id="evt_test_456",
            source="ourlives",
            token_count=200,
            amount_cents=2000,
        )
        self.assertEqual(event.source, "ourlives")

    def test_str_representation(self):
        event = StripeEvent.objects.create(
            stripe_event_id="evt_test_789",
            source="ourlives",
            token_count=50,
            amount_cents=500,
        )
        self.assertEqual(str(event), "ourlives:evt_test_789")


class WebhookViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = "/stripe/webhook/"
        self.settings = AppSettings.get_solo()
        self.settings.total_tokens = 100
        self.settings.save()

    def _build_valid_payload(self, event_id="evt_test_001", source="ourlives", token_count="50", app_settings_id=None, amount_total=1000, presentment_currency=None, presentment_amount=None):
        if app_settings_id is None:
            app_settings_id = self.settings.pk
        data = {
            "id": event_id,
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {
                        "source": source,
                        "token_count": token_count,
                        "app_settings_id": str(app_settings_id),
                    },
                    "amount_total": amount_total,
                },
            },
        }
        if presentment_currency and presentment_amount is not None:
            data["data"]["object"]["presentment_details"] = {
                "presentment_currency": presentment_currency,
                "presentment_amount": presentment_amount,
            }
        return json.dumps(data)

    def _send_webhook(self, payload, sig_header="test_sig"):
        return self.client.post(
            self.url,
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=sig_header,
        )

    @patch("ourlives.views.verify_webhook_signature")
    def test_valid_event_increments_tokens(self, mock_verify):
        mock_verify.return_value = json.loads(self._build_valid_payload())
        response = self._send_webhook(self._build_valid_payload())
        self.assertEqual(response.status_code, 200)
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.total_tokens, 150)

    @patch("ourlives.views.verify_webhook_signature")
    def test_duplicate_event_is_idempotent(self, mock_verify):
        payload_data = self._build_valid_payload()
        mock_verify.return_value = json.loads(payload_data)
        self._send_webhook(payload_data)
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.total_tokens, 150)
        response = self._send_webhook(payload_data)
        self.assertEqual(response.status_code, 200)
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.total_tokens, 150)

    def test_missing_signature_returns_400(self):
        response = self.client.post(
            self.url,
            data=self._build_valid_payload(),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_wrong_content_type_returns_400(self):
        response = self.client.post(
            self.url,
            data=self._build_valid_payload(),
            content_type="text/plain",
            HTTP_STRIPE_SIGNATURE="test_sig",
        )
        self.assertEqual(response.status_code, 400)

    @patch("ourlives.views.verify_webhook_signature")
    def test_unknown_source_logs_warning_returns_200(self, mock_verify):
        payload = self._build_valid_payload(source="unknown_app")
        mock_verify.return_value = json.loads(payload)
        response = self._send_webhook(payload)
        self.assertEqual(response.status_code, 200)
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.total_tokens, 100)

    @patch("ourlives.views.verify_webhook_signature")
    def test_missing_source_metadata_returns_200(self, mock_verify):
        payload = json.dumps({
            "id": "evt_test_no_source",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "metadata": {},
                    "amount_total": 1000,
                },
            },
        })
        mock_verify.return_value = json.loads(payload)
        response = self._send_webhook(payload)
        self.assertEqual(response.status_code, 200)
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.total_tokens, 100)

    @patch("ourlives.views.verify_webhook_signature")
    def test_unhandled_event_type_returns_200(self, mock_verify):
        payload = json.dumps({
            "id": "evt_test_unhandled",
            "type": "charge.succeeded",
            "data": {"object": {}},
        })
        mock_verify.return_value = json.loads(payload)
        response = self._send_webhook(payload)
        self.assertEqual(response.status_code, 200)
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.total_tokens, 100)

    @patch("ourlives.views.verify_webhook_signature")
    def test_app_settings_id_mismatch_still_applies_tokens(self, mock_verify):
        payload = self._build_valid_payload(event_id="evt_test_mismatch", app_settings_id=99999)
        mock_verify.return_value = json.loads(payload)
        response = self._send_webhook(payload)
        self.assertEqual(response.status_code, 200)
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.total_tokens, 150)

    @patch("ourlives.views.verify_webhook_signature")
    def test_dispatches_ourlives_source_to_handler(self, mock_verify):
        payload = self._build_valid_payload(event_id="evt_test_dispatch")
        mock_verify.return_value = json.loads(payload)
        response = self._send_webhook(payload)
        self.assertEqual(response.status_code, 200)
        self.settings.refresh_from_db()
        self.assertEqual(self.settings.total_tokens, 150)

    @patch("ourlives.views.verify_webhook_signature")
    def test_webhook_stores_presentment_details(self, mock_verify):
        payload = self._build_valid_payload(
            event_id="evt_test_presentment",
            presentment_currency="eur",
            presentment_amount=920,
        )
        mock_verify.return_value = json.loads(payload)
        response = self._send_webhook(payload)
        self.assertEqual(response.status_code, 200)
        event = StripeEvent.objects.get(stripe_event_id="evt_test_presentment")
        self.assertEqual(event.presentment_currency, "eur")
        self.assertEqual(event.presentment_amount, 920)

    @patch("ourlives.views.verify_webhook_signature")
    def test_webhook_handles_missing_presentment_details(self, mock_verify):
        payload = self._build_valid_payload(event_id="evt_test_no_presentment")
        mock_verify.return_value = json.loads(payload)
        response = self._send_webhook(payload)
        self.assertEqual(response.status_code, 200)
        event = StripeEvent.objects.get(stripe_event_id="evt_test_no_presentment")
        self.assertEqual(event.presentment_currency, "")
        self.assertIsNone(event.presentment_amount)


class SyncStripePriceCommandTests(TestCase):
    @patch("stripe.Product.create")
    @patch("stripe.Price.create")
    def test_creates_product_and_price(self, mock_price_create, mock_product_create):
        mock_product = type("Product", (), {"id": "prod_test_123"})()
        mock_product_create.return_value = mock_product
        mock_price = type("Price", (), {"id": "price_test_123"})()
        mock_price_create.return_value = mock_price

        settings = AppSettings.get_solo()
        settings.price_per_token = D("0.50")
        settings.save()

        out = io.StringIO()
        call_command("sync_stripe_price", stdout=out)

        self.assertIn("Created product: prod_test_123", out.getvalue())
        self.assertIn("Price created: price_test_123", out.getvalue())

        settings.refresh_from_db()
        self.assertEqual(settings.stripe_product_id, "prod_test_123")
        self.assertEqual(settings.stripe_price_id, "price_test_123")

        mock_price_create.assert_called_once_with(
            product="prod_test_123",
            unit_amount=50,
            currency="usd",
        )

    @patch("stripe.Product.create")
    @patch("stripe.Price.create")
    def test_arches_existing_price_on_re_run(self, mock_price_create, mock_product_create):
        mock_product = type("Product", (), {"id": "prod_test_123"})()
        mock_product_create.return_value = mock_product

        settings = AppSettings.get_solo()
        settings.price_per_token = D("0.50")
        settings.stripe_product_id = "prod_test_123"
        settings.stripe_price_id = "price_old_456"
        settings.save()

        with patch("stripe.Price.modify") as mock_modify:
            mock_price = type("Price", (), {"id": "price_new_789"})()
            mock_price_create.return_value = mock_price

            out = io.StringIO()
            call_command("sync_stripe_price", stdout=out)

            self.assertIn("Archived old price: price_old_456", out.getvalue())
            self.assertIn("Price created: price_new_789", out.getvalue())
            mock_modify.assert_called_once_with("price_old_456", active=False)

            settings.refresh_from_db()
            self.assertEqual(settings.stripe_price_id, "price_new_789")

    def test_skips_when_price_per_token_is_zero(self):
        settings = AppSettings.get_solo()
        settings.price_per_token = D("0")
        settings.save()

        out = io.StringIO()
        call_command("sync_stripe_price", stdout=out)

        self.assertIn("Skipping", out.getvalue())
        self.assertIn("purchases disabled", out.getvalue())

    @patch("stripe.Product.create")
    @patch("stripe.Price.create")
    def test_uses_existing_product_from_settings(self, mock_price_create, mock_product_create):
        settings = AppSettings.get_solo()
        settings.price_per_token = D("1.00")
        settings.stripe_product_id = "prod_existing_123"
        settings.save()

        mock_price = type("Price", (), {"id": "price_test_456"})()
        mock_price_create.return_value = mock_price

        out = io.StringIO()
        call_command("sync_stripe_price", stdout=out)

        self.assertIn("Reusing product: prod_existing_123", out.getvalue())
        mock_product_create.assert_not_called()


class AppSettingsAdminTests(TestCase):
    def setUp(self):
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory
        from ourlives.admin import AppSettingsAdmin

        self.factory = RequestFactory()
        self.site = AdminSite()
        self.admin = AppSettingsAdmin(AppSettings, self.site)
        self.superuser = User.objects.create_superuser(
            username="su", email="su@test.com", password="x",
        )
        self.staff = User.objects.create_user(
            username="staff", email="staff@test.com", password="x",
            is_staff=True,
        )

    def test_superuser_sees_api_fields_as_editable(self):
        request = self.factory.get("/")
        request.user = self.superuser
        readonly = self.admin.get_readonly_fields(request)
        self.assertNotIn("storage_base_url", readonly)

    def test_non_superuser_staff_sees_api_fields_as_readonly(self):
        request = self.factory.get("/")
        request.user = self.staff
        readonly = self.admin.get_readonly_fields(request)
        self.assertIn("storage_base_url", readonly)


class PaymentSuccessViewTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_payment_success_redirects_to_settings_with_token_count(self):
        response = self.client.get("/stripe/success/", {"token_count": "50", "session_id": "cs_test_123"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("admin:ourlives_appsettings_change"))

    def test_payment_success_redirects_without_token_count(self):
        response = self.client.get("/stripe/success/", {"session_id": "cs_test_123"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("admin:ourlives_appsettings_change"))

    def test_payment_success_redirects_without_params(self):
        response = self.client.get("/stripe/success/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("admin:ourlives_appsettings_change"))


class CountryTests(TestCase):
    def setUp(self):
        call_command("base_loaddata")

    def test_create_country(self):
        country = Country.objects.create(iso2="ZZ", iso3="ZZZ", name="Testland", region="EU")
        self.assertEqual(country.iso2, "ZZ")
        self.assertEqual(country.iso3, "ZZZ")
        self.assertEqual(country.name, "Testland")
        self.assertEqual(str(country), "Testland")

    def test_duplicate_iso2_raises_error(self):
        Country.objects.create(iso2="ZZ", iso3="ZZZ", name="Testland")
        with self.assertRaises(IntegrityError):
            Country.objects.create(iso2="ZZ", iso3="YYY", name="Otherland")

    def test_duplicate_iso3_raises_error(self):
        Country.objects.create(iso2="ZZ", iso3="ZZZ", name="Testland")
        with self.assertRaises(IntegrityError):
            Country.objects.create(iso2="YY", iso3="ZZZ", name="Otherland")

    def test_duplicate_name_raises_error(self):
        Country.objects.create(iso2="ZZ", iso3="ZZZ", name="Testland")
        with self.assertRaises(IntegrityError):
            Country.objects.create(iso2="YY", iso3="YYY", name="Testland")


class RepTests(TestCase):
    def setUp(self):
        call_command("base_loaddata")

    def test_create_rep(self):
        rep = Rep.objects.create(first_name="John", last_name="Doe", email="john@ourlivesapp.com")
        self.assertEqual(rep.first_name, "John")
        self.assertEqual(rep.last_name, "Doe")
        self.assertEqual(rep.email, "john@ourlivesapp.com")
        self.assertEqual(str(rep), "John Doe")

    def test_duplicate_email_raises_error(self):
        Rep.objects.create(first_name="John", last_name="Doe", email="john@ourlivesapp.com")
        with self.assertRaises(IntegrityError):
            Rep.objects.create(first_name="Jane", last_name="Smith", email="john@ourlivesapp.com")

    def test_no_fixture_rows(self):
        # Rep has no base fixture — base_loaddata must not create any
        self.assertEqual(Rep.objects.count(), 0)


class ContactTypeTests(TestCase):
    def setUp(self):
        call_command("base_loaddata")

    def test_create_contact_type(self):
        ct = ContactType.objects.create(code="testcode", name="Test Contact")
        self.assertEqual(ct.code, "testcode")
        self.assertEqual(str(ct), "Test Contact")

    def test_duplicate_code_raises_error(self):
        ContactType.objects.create(code="testcode", name="Test Contact")
        with self.assertRaises(IntegrityError):
            ContactType.objects.create(code="testcode", name="Other Contact")

    def test_duplicate_name_raises_error(self):
        ContactType.objects.create(code="testcode", name="Test Contact")
        with self.assertRaises(IntegrityError):
            ContactType.objects.create(code="othercode", name="Test Contact")


class CodeTypeTests(TestCase):
    def setUp(self):
        call_command("base_loaddata")

    def test_create_code_type(self):
        ct = CodeType.objects.create(code="test_code", name="Test Code", max_codes=10)
        self.assertEqual(ct.code, "test_code")
        self.assertEqual(ct.max_codes, 10)
        self.assertEqual(str(ct), "Test Code")

    def test_duplicate_code_raises_error(self):
        CodeType.objects.create(code="test_code", name="Test Code", max_codes=5)
        with self.assertRaises(IntegrityError):
            CodeType.objects.create(code="test_code", name="Other Code", max_codes=5)

    def test_duplicate_name_raises_error(self):
        CodeType.objects.create(code="test_code", name="Test Code", max_codes=5)
        with self.assertRaises(IntegrityError):
            CodeType.objects.create(code="other_code", name="Test Code", max_codes=5)


class OrderTypeTests(TestCase):
    def setUp(self):
        call_command("base_loaddata")

    def test_create_order_type(self):
        ot = OrderType.objects.create(code="custom", name="Custom Order")
        self.assertEqual(ot.code, "custom")
        self.assertEqual(str(ot), "Custom Order")

    def test_duplicate_code_raises_error(self):
        OrderType.objects.create(code="custom", name="Custom Order")
        with self.assertRaises(IntegrityError):
            OrderType.objects.create(code="custom", name="Other Order")

    def test_duplicate_name_raises_error(self):
        OrderType.objects.create(code="custom", name="Custom Order")
        with self.assertRaises(IntegrityError):
            OrderType.objects.create(code="othercode", name="Custom Order")


class Phase1FixturesTests(TestCase):
    def test_base_loaddata_loads_all_fixtures(self):
        call_command("base_loaddata")
        self.assertEqual(Country.objects.count(), 249)
        self.assertEqual(ContactType.objects.count(), 4)
        self.assertEqual(CodeType.objects.count(), 2)
        self.assertEqual(OrderType.objects.count(), 4)
        self.assertEqual(Rep.objects.count(), 0)
        # Explicit PKs alphabetical-from-1
        self.assertEqual(Country.objects.get(pk=1).iso2, "AD")
        self.assertEqual(Country.objects.get(pk=249).iso2, "ZW")
        self.assertEqual(ContactType.objects.get(pk=1).code, "billing")
        self.assertEqual(CodeType.objects.get(pk=1).code, "up_to_20")
        self.assertEqual(CodeType.objects.get(pk=2).code, "up_to_5")
        self.assertEqual(OrderType.objects.get(pk=1).code, "pilot")

    def test_fixture_idempotent(self):
        call_command("base_loaddata")
        counts = (
            Country.objects.count(),
            ContactType.objects.count(),
            CodeType.objects.count(),
            OrderType.objects.count(),
        )
        call_command("base_loaddata")
        self.assertEqual(
            counts,
            (
                Country.objects.count(),
                ContactType.objects.count(),
                CodeType.objects.count(),
                OrderType.objects.count(),
            ),
        )


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class LookupAdminTests(TestCase):
    def setUp(self):
        call_command("base_loaddata")
        self.admin = User.objects.create_superuser("lookup_admin", "lookup@test.com", "x")
        self.client = Client()
        self.client.force_login(self.admin)

    def test_lookup_changelists_render(self):
        for url in ("country", "rep", "contacttype", "codetype", "ordertype"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(f"/admin/ourlives/{url}/").status_code, 200)

    def test_country_add_and_delete_blocked(self):
        country = Country.objects.first()
        self.assertEqual(self.client.get("/admin/ourlives/country/add/").status_code, 403)
        self.assertEqual(
            self.client.post(f"/admin/ourlives/country/{country.pk}/delete/", {"post": "yes"}).status_code,
            403,
        )

    def test_country_inline_active_toggle_persists(self):
        country = Country.objects.filter(active=True).first()
        self.client.post("/admin/ourlives/country/", {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",
            "form-0-id": str(country.pk),
            "_save": "Save",
        })
        country.refresh_from_db()
        self.assertFalse(country.active)

    def test_rep_crud(self):
        rep = Rep.objects.create(first_name="Jane", last_name="Doe", email="jane@ourlivesapp.com")
        self.assertEqual(self.client.get("/admin/ourlives/rep/").status_code, 200)
        self.assertEqual(
            self.client.get(f"/admin/ourlives/rep/{rep.pk}/change/").status_code, 200,
        )

    def test_lookup_export_actions_registered(self):
        from django.contrib import admin as admin_site

        for model in (Country, Rep, ContactType, CodeType, OrderType):
            with self.subTest(model=model.__name__):
                self.assertIn("export_selected", admin_site.site._registry[model].actions)

    def test_invitation_code_autocomplete_and_editable(self):
        from django.contrib import admin as admin_site

        ma = admin_site.site._registry[InvitationCode]
        self.assertEqual(tuple(ma.autocomplete_fields), ("project", "organization"))
        self.assertEqual(tuple(ma.list_editable), ("is_active",))
        self.assertEqual(self.client.get("/admin/ourlives/invitationcode/").status_code, 200)

    def test_search_filter_tuning(self):
        from django.contrib import admin as admin_site
        from project.admin_base import UsageBucketFilter, UsageMaxFilter, UsageMinFilter

        ma = admin_site.site._registry[Project]
        self.assertEqual(tuple(ma.search_fields), ("name", "description"))

        ma = admin_site.site._registry[Organization]
        self.assertEqual(tuple(ma.list_filter), ("assigned_rep",))
        self.assertEqual(
            tuple(ma.search_fields),
            ("name", "description", "assigned_rep__first_name", "assigned_rep__last_name", "assigned_rep__email"),
        )

        ma = admin_site.site._registry[InvitationCode]
        self.assertEqual(
            tuple(ma.list_filter),
            ("is_active", "project", "organization", "code_type", UsageBucketFilter, UsageMinFilter, UsageMaxFilter),
        )
        self.assertEqual(
            tuple(ma.search_fields),
            ("^code", "project__name", "organization__name", "order__order_number", "code_type__code", "code_type__name"),
        )
        self.assertTrue(ma.search_help_text)

        ma = admin_site.site._registry[Country]
        self.assertEqual(tuple(ma.search_fields), ("^iso2", "^iso3", "name"))

        for model in (ContactType, CodeType, OrderType):
            with self.subTest(model=model.__name__):
                self.assertEqual(
                    tuple(admin_site.site._registry[model].search_fields),
                    ("^code", "name", "description"),
                )

        ma = admin_site.site._registry[StripeEvent]
        self.assertEqual(
            tuple(ma.search_fields), ("=stripe_event_id", "source", "presentment_currency")
        )
        self.assertTrue(ma.search_help_text)
        self.assertFalse(ma.has_add_permission(self.admin))


class CurrencyTests(TestCase):
    def test_create_currency_with_countries(self):
        de = Country.objects.create(iso2="DE", iso3="DEU", name="Germany")
        fr = Country.objects.create(iso2="FR", iso3="FRA", name="France")
        currency = Currency.objects.create(
            code="EUR", name="Euro", symbol_left="€",
            exchange_rate=Decimal("0.92"),
        )
        currency.countries.add(de, fr)
        self.assertEqual(currency.code, "EUR")
        self.assertEqual(set(currency.countries.all()), {de, fr})
        self.assertTrue(currency.active)
        self.assertEqual(str(currency), "EUR")

    def test_countries_are_optional(self):
        currency = Currency.objects.create(code="USD", name="US Dollar", exchange_rate=Decimal("1.00"))
        self.assertEqual(currency.countries.count(), 0)

    def test_shared_currency_across_countries(self):
        de = Country.objects.create(iso2="DE", iso3="DEU", name="Germany")
        fr = Country.objects.create(iso2="FR", iso3="FRA", name="France")
        eur = Currency.objects.create(code="EUR", name="Euro", exchange_rate=Decimal("0.92"))
        eur.countries.add(de, fr)
        self.assertIn(eur, de.currencies.all())
        self.assertIn(eur, fr.currencies.all())

    def test_country_delete_removes_only_the_link(self):
        de = Country.objects.create(iso2="DE", iso3="DEU", name="Germany")
        currency = Currency.objects.create(code="EUR", name="Euro", exchange_rate=Decimal("0.92"))
        currency.countries.add(de)
        de.delete()
        currency.refresh_from_db()
        self.assertEqual(currency.countries.count(), 0)
        self.assertTrue(Currency.objects.filter(code="EUR").exists())

    def test_duplicate_code_raises_error(self):
        Currency.objects.create(code="TTD", name="Test Dollar", exchange_rate=Decimal("1.00"))
        with self.assertRaises(IntegrityError):
            Currency.objects.create(code="TTD", name="Other Dollar", exchange_rate=Decimal("2.00"))


class ProductTests(TestCase):
    def setUp(self):
        self.currency = Currency.objects.create(code="USD", name="US Dollar", symbol_left="$", exchange_rate=Decimal("1.00"))

    def test_create_product(self):
        product = Product.objects.create(
            currency=self.currency, name="Micro Pilot", tier="micro",
            unit_price=Decimal("995.00"), description="Pilot bundle",
        )
        self.assertEqual(product.name, "Micro Pilot")
        self.assertEqual(product.currency, self.currency)
        self.assertTrue(product.active)
        self.assertEqual(str(product), "Micro Pilot")

    def test_currency_protected(self):
        Product.objects.create(currency=self.currency, name="Micro Pilot", unit_price=Decimal("995.00"))
        with self.assertRaises(ProtectedError):
            self.currency.delete()


class ContactTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Test Org")
        self.contact_type = ContactType.objects.create(code="primary", name="Primary Contact")

    def test_create_contact(self):
        contact = Contact.objects.create(
            organization=self.organization, contact_type=self.contact_type,
            first_name="Alice", last_name="Smith",
            email="alice@acme.com", phone="+44 7700 900123",
        )
        self.assertEqual(contact.email, "alice@acme.com")
        self.assertEqual(str(contact), "Alice Smith")

    def test_organization_delete_cascades(self):
        Contact.objects.create(
            organization=self.organization, contact_type=self.contact_type,
            first_name="Alice", last_name="Smith", email="alice@acme.com",
        )
        self.organization.delete()
        self.assertEqual(Contact.objects.count(), 0)

    def test_contact_type_protected(self):
        Contact.objects.create(
            organization=self.organization, contact_type=self.contact_type,
            first_name="Alice", last_name="Smith", email="alice@acme.com",
        )
        with self.assertRaises(ProtectedError):
            self.contact_type.delete()


class OrganizationAddressTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Test Org")
        self.country = Country.objects.create(iso2="ZZ", iso3="ZZZ", name="Testland")

    def test_create_address(self):
        address = OrganizationAddress.objects.create(
            organization=self.organization, country=self.country,
            line1="10 Downing St", city="London", zip="SW1A 2AA", is_primary=True,
        )
        self.assertEqual(address.city, "London")
        self.assertTrue(address.is_primary)
        self.assertEqual(str(address), "10 Downing St, London")

    def test_filter_primary_address(self):
        OrganizationAddress.objects.create(
            organization=self.organization, country=self.country,
            line1="10 Downing St", city="London", zip="SW1A 2AA", is_primary=True,
        )
        OrganizationAddress.objects.create(
            organization=self.organization, country=self.country,
            line1="221B Baker St", city="London", zip="NW1 6XE", is_primary=False,
        )
        primary = OrganizationAddress.objects.filter(organization=self.organization, is_primary=True)
        self.assertEqual(primary.count(), 1)
        self.assertEqual(primary.get().line1, "10 Downing St")

    def test_country_protected(self):
        OrganizationAddress.objects.create(
            organization=self.organization, country=self.country,
            line1="10 Downing St", city="London", zip="SW1A 2AA",
        )
        with self.assertRaises(ProtectedError):
            self.country.delete()

    def test_organization_delete_cascades(self):
        OrganizationAddress.objects.create(
            organization=self.organization, country=self.country,
            line1="10 Downing St", city="London", zip="SW1A 2AA",
        )
        self.organization.delete()
        self.assertEqual(OrganizationAddress.objects.count(), 0)


class CurrencyFixtureTests(TestCase):
    def setUp(self):
        call_command("base_loaddata")

    def test_base_loaddata_seeds_twelve_currencies(self):
        codes = set(Currency.objects.values_list("code", flat=True))
        self.assertEqual(codes, {
            "USD", "EUR", "JPY", "GBP", "CNY", "CHF",
            "AUD", "CAD", "HKD", "SGD", "NZD", "ZAR",
        })
        self.assertTrue(all(c.active for c in Currency.objects.all()))

    def test_fixture_currencies_link_to_using_countries(self):
        links = {
            code: set(Currency.objects.get(code=code).countries.values_list("iso2", flat=True))
            for code in ("USD", "EUR", "GBP", "ZAR")
        }
        self.assertEqual(links["USD"], {"US", "EC", "SV", "ZW", "PA", "TL", "MH", "FM", "PW"})
        self.assertEqual(len(links["EUR"]), 20)
        self.assertIn("DE", links["EUR"])
        self.assertIn("FR", links["EUR"])
        self.assertEqual(links["GBP"], {"GB"})
        self.assertEqual(links["ZAR"], {"ZA", "LS", "NA", "SZ"})

    def test_fixture_idempotent(self):
        call_command("base_loaddata")
        self.assertEqual(Currency.objects.count(), 12)

    def test_seeded_currency_unblocks_product_creation(self):
        usd = Currency.objects.get(code="USD")
        product = Product.objects.create(currency=usd, name="Micro Pilot", unit_price=Decimal("995.00"))
        self.assertEqual(product.currency, usd)


class ProductFixtureTests(TestCase):
    def setUp(self):
        call_command("base_loaddata")

    def test_base_loaddata_seeds_twelve_products(self):
        self.assertEqual(Product.objects.count(), 12)
        self.assertTrue(all(p.active for p in Product.objects.all()))

    def test_fixture_products_link_to_pilot_currencies(self):
        links = {
            (p.currency.code, p.tier): p.name
            for p in Product.objects.select_related("currency").all()
        }
        self.assertEqual(links, {
            ("USD", "micro"): "US Micro Pilot",
            ("USD", "regional"): "US Regional Pilot",
            ("USD", "enterprise"): "US Enterprise Pilot",
            ("GBP", "micro"): "UK Micro Pilot",
            ("GBP", "regional"): "UK Regional Pilot",
            ("GBP", "enterprise"): "UK Enterprise Pilot",
            ("CAD", "micro"): "Canada Micro Pilot",
            ("CAD", "regional"): "Canada Regional Pilot",
            ("CAD", "enterprise"): "Canada Enterprise Pilot",
            ("ZAR", "micro"): "South Africa Micro Pilot",
            ("ZAR", "regional"): "South Africa Regional Pilot",
            ("ZAR", "enterprise"): "South Africa Enterprise Pilot",
        })

    def test_fixture_idempotent(self):
        call_command("base_loaddata")
        self.assertEqual(Product.objects.count(), 12)

    def test_seeded_product_unblocks_order_item(self):
        product = Product.objects.get(name="US Micro Pilot")
        organization = Organization.objects.create(name="Test Org")
        rep = Rep.objects.create(first_name="John", last_name="Doe", email="john@ourlivesapp.com")
        order = Order.objects.create(organization=organization, rep=rep, po_number="PO-001")
        item = OrderItem.objects.create(
            order=order, product=product,
            quantity=2, unit_price=Decimal("995.00"),
        )
        self.assertEqual(item.line_total, Decimal("1990.00"))
        with self.assertRaises(ProtectedError):
            product.delete()

    def test_no_per_sale_fixture_rows(self):
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)
        self.assertEqual(Contact.objects.count(), 0)
        self.assertEqual(OrganizationAddress.objects.count(), 0)
        self.assertEqual(Rep.objects.count(), 0)
        self.assertEqual(InvitationCode.objects.count(), 0)
        self.assertEqual(StripeEvent.objects.count(), 0)
        self.assertEqual(AppSettings.get_solo().total_tokens, 0)


class OrderTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Test Org")
        self.rep = Rep.objects.create(first_name="John", last_name="Doe", email="john@ourlivesapp.com")
        self.pilot = OrderType.objects.create(code="pilot", name="Pilot Order")
        self.standard = OrderType.objects.create(code="standard", name="Standard Order")

    def _create_order(self, **kwargs):
        defaults = {"organization": self.organization, "rep": self.rep, "po_number": "PO-001"}
        defaults.update(kwargs)
        return Order.objects.create(**defaults)

    def test_auto_generated_order_number(self):
        order = self._create_order()
        self.assertTrue(order.order_number.startswith("OL-"))
        self.assertEqual(str(order), order.order_number)
        other = self._create_order()
        self.assertNotEqual(order.order_number, other.order_number)

    def test_explicit_order_number_and_uniqueness(self):
        order = self._create_order(order_number="OL-82")
        self.assertEqual(order.order_number, "OL-82")
        with self.assertRaises(IntegrityError):
            self._create_order(order_number="OL-82")

    def test_organization_protected(self):
        self._create_order()
        with self.assertRaises(ProtectedError):
            self.organization.delete()

    def test_rep_protected(self):
        self._create_order()
        with self.assertRaises(ProtectedError):
            self.rep.delete()

    def test_contacts_nullable_and_protected(self):
        order = self._create_order()
        self.assertIsNone(order.primary_contact)
        self.assertIsNone(order.invoice_contact)
        contact_type = ContactType.objects.create(code="primary", name="Primary Contact")
        contact = Contact.objects.create(
            organization=self.organization, contact_type=contact_type,
            first_name="Alice", last_name="Smith", email="alice@acme.com",
        )
        order.primary_contact = contact
        order.save()
        with self.assertRaises(ProtectedError):
            contact.delete()

    def test_m2m_add_marks_pilot(self):
        order = self._create_order()
        self.assertFalse(order.is_pilot_order)
        order.order_types.add(self.pilot)
        self.assertTrue(order.is_pilot_order)

    def test_m2m_remove_clears_pilot(self):
        order = self._create_order()
        order.order_types.add(self.pilot)
        order.order_types.remove(self.pilot)
        self.assertFalse(order.is_pilot_order)

    def test_multiple_types_coexist(self):
        order = self._create_order()
        order.order_types.add(self.pilot, self.standard)
        self.assertEqual(order.order_types.count(), 2)
        self.assertTrue(order.is_pilot_order)

    def test_unsaved_order_is_not_pilot(self):
        order = Order(organization=self.organization, rep=self.rep, po_number="PO-002")
        self.assertFalse(order.is_pilot_order)

    def test_no_single_order_type_column(self):
        self.assertNotIn("order_type", [f.name for f in Order._meta.get_fields()])

    def test_total_agreed_price_computed(self):
        order = self._create_order(number_of_scans=500, cost_per_scan=Decimal("2.50"))
        self.assertEqual(order.total_agreed_price, Decimal("1250.00"))

    def test_total_agreed_price_missing_inputs_returns_zero(self):
        self.assertEqual(self._create_order().total_agreed_price, Decimal("0"))
        self.assertEqual(
            self._create_order(number_of_scans=500).total_agreed_price, Decimal("0"),
        )
        self.assertEqual(
            self._create_order(cost_per_scan=Decimal("2.50")).total_agreed_price, Decimal("0"),
        )

    def test_no_total_agreed_price_column(self):
        self.assertNotIn("total_agreed_price", [f.name for f in Order._meta.get_fields()])

    def test_total_order_value_merges_agreed_and_items(self):
        order = self._create_order(number_of_scans=500, cost_per_scan=Decimal("2.50"))
        currency = Currency.objects.create(code="TTT", name="Test", exchange_rate=Decimal("1.00"))
        product = Product.objects.create(currency=currency, name="Widget", unit_price=Decimal("20.00"))
        OrderItem.objects.create(order=order, product=product, quantity=2, unit_price=Decimal("20.00"))
        self.assertEqual(order.total_order_value, Decimal("1290.00"))

    def test_total_order_value_nulls_treated_as_zero(self):
        order = self._create_order()
        currency = Currency.objects.create(code="UUU", name="Test2", exchange_rate=Decimal("1.00"))
        product = Product.objects.create(currency=currency, name="Gadget", unit_price=Decimal("20.00"))
        OrderItem.objects.create(order=order, product=product, quantity=1, unit_price=Decimal("20.00"))
        self.assertEqual(order.total_order_value, Decimal("20.00"))

    def test_total_order_value_zero_without_scans_or_items(self):
        order = self._create_order()
        self.assertEqual(order.total_order_value, Decimal("0"))

    def test_no_total_order_value_column(self):
        self.assertNotIn("total_order_value", [f.name for f in Order._meta.get_fields()])

    def test_currency_delete_sets_null(self):
        currency = Currency.objects.create(code="USD", name="US Dollar", exchange_rate=Decimal("1.00"))
        order = self._create_order(currency=currency, pilot_currency=currency)
        currency.delete()
        order.refresh_from_db()
        self.assertIsNone(order.currency)
        self.assertIsNone(order.pilot_currency)

    def test_billing_milestones_default_unset(self):
        order = self._create_order()
        self.assertFalse(order.invoice_sent)
        self.assertIsNone(order.invoice_sent_on)
        self.assertFalse(order.invoice_paid)
        self.assertIsNone(order.invoice_paid_on)
        self.assertFalse(order.commission_paid)
        self.assertIsNone(order.commission_paid_on)

    def test_billing_tick_without_date_persists(self):
        order = self._create_order(invoice_sent=True)
        order.refresh_from_db()
        self.assertTrue(order.invoice_sent)
        self.assertIsNone(order.invoice_sent_on)

    def test_billing_date_without_tick_stays_unticked(self):
        order = self._create_order(invoice_paid_on=date(2026, 9, 22))
        order.refresh_from_db()
        self.assertFalse(order.invoice_paid)
        self.assertEqual(order.invoice_paid_on, date(2026, 9, 22))

    def test_billing_full_pair_persists(self):
        order = self._create_order(commission_paid=True, commission_paid_on=date(2026, 9, 22))
        order.refresh_from_db()
        self.assertTrue(order.commission_paid)
        self.assertEqual(order.commission_paid_on, date(2026, 9, 22))

    def test_rep_commission_note_defaults_empty(self):
        self.assertEqual(self._create_order().rep_commission_note, "")

    def test_rep_commission_note_persists_verbatim(self):
        order = self._create_order(rep_commission_note="15% Q3 promo")
        order.refresh_from_db()
        self.assertEqual(order.rep_commission_note, "15% Q3 promo")


class OrderItemTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(name="Test Org")
        self.rep = Rep.objects.create(first_name="John", last_name="Doe", email="john@ourlivesapp.com")
        self.currency = Currency.objects.create(code="USD", name="US Dollar", exchange_rate=Decimal("1.00"))
        self.product = Product.objects.create(
            currency=self.currency, name="Micro Pilot", unit_price=Decimal("995.00"),
        )
        self.order = Order.objects.create(
            organization=self.organization, rep=self.rep, po_number="PO-001",
        )

    def test_create_item_and_line_total(self):
        item = OrderItem.objects.create(
            order=self.order, product=self.product,
            quantity=2, unit_price=Decimal("3995.00"),
        )
        self.assertEqual(item.line_total, Decimal("7990.00"))
        self.assertIn("Micro Pilot", str(item))

    def test_order_delete_cascades(self):
        OrderItem.objects.create(
            order=self.order, product=self.product,
            quantity=1, unit_price=Decimal("995.00"),
        )
        self.order.delete()
        self.assertEqual(OrderItem.objects.count(), 0)

    def test_product_protected(self):
        OrderItem.objects.create(
            order=self.order, product=self.product,
            quantity=1, unit_price=Decimal("995.00"),
        )
        with self.assertRaises(ProtectedError):
            self.product.delete()

    def test_duplicate_product_lines_allowed(self):
        for _ in range(2):
            OrderItem.objects.create(
                order=self.order, product=self.product,
                quantity=1, unit_price=Decimal("995.00"),
            )
        self.assertEqual(OrderItem.objects.count(), 2)


class OrderLinkAlterationTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        self.organization = Organization.objects.create(name="Test Org")
        self.rep = Rep.objects.create(first_name="John", last_name="Doe", email="john@ourlivesapp.com")
        AppSettings.get_solo()
        AppSettings.objects.update(total_tokens=100)

    def test_backwards_compatible_creation(self):
        code = InvitationCode.objects.create(
            project=self.project, organization=self.organization, max_use=10,
        )
        self.assertIsNone(self.organization.assigned_rep)
        self.assertIsNone(code.order)
        self.assertIsNone(code.code_type)
        self.assertIsNone(code.sequence)

    def test_rep_delete_sets_null_on_organization(self):
        self.organization.assigned_rep = self.rep
        self.organization.save()
        self.rep.delete()
        self.organization.refresh_from_db()
        self.assertIsNone(self.organization.assigned_rep)

    def test_order_protected_from_invitation_code(self):
        order = Order.objects.create(
            organization=self.organization, rep=self.rep, po_number="PO-001",
        )
        InvitationCode.objects.create(
            project=self.project, organization=self.organization, max_use=10, order=order,
        )
        with self.assertRaises(ProtectedError):
            order.delete()

    def test_code_type_protected_from_invitation_code(self):
        code_type = CodeType.objects.create(code="up_to_5", name="Up to 5", max_codes=5)
        InvitationCode.objects.create(
            project=self.project, organization=self.organization, max_use=10, code_type=code_type,
        )
        with self.assertRaises(ProtectedError):
            code_type.delete()

    def test_link_fields_round_trip(self):
        order = Order.objects.create(
            organization=self.organization, rep=self.rep, po_number="PO-001",
        )
        code_type = CodeType.objects.create(code="up_to_5", name="Up to 5", max_codes=5)
        code = InvitationCode.objects.create(
            project=self.project, organization=self.organization, max_use=10,
            order=order, code_type=code_type, sequence=3,
        )
        code.refresh_from_db()
        self.assertEqual(code.order, order)
        self.assertEqual(code.code_type, code_type)
        self.assertEqual(code.sequence, 3)


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class CrmAdminRegistrationTests(TestCase):
    def setUp(self):
        call_command("base_loaddata")
        self.admin = User.objects.create_superuser("crm_admin", "crm@test.com", "x")
        self.client = Client()
        self.client.force_login(self.admin)

    def test_changelists_render(self):
        for url in ("currency", "product", "contact", "organizationaddress", "order", "orderitem"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(f"/admin/ourlives/{url}/").status_code, 200)

    def test_admin_options_match_spec(self):
        from django.contrib import admin as admin_site

        from ourlives.admin import (
            ContactAdmin,
            CurrencyAdmin,
            OrderAdmin,
            OrderItemAdmin,
            OrganizationAddressAdmin,
            ProductAdmin,
        )

        ma = admin_site.site._registry[Currency]
        self.assertIsInstance(ma, CurrencyAdmin)
        self.assertEqual(tuple(ma.list_display), ("code", "name", "exchange_rate", "active"))
        self.assertEqual(tuple(ma.list_filter), ("active", "countries"))
        self.assertEqual(tuple(ma.search_fields), ("^code", "name"))
        self.assertEqual(tuple(ma.list_editable), ("active",))
        self.assertEqual(tuple(ma.filter_horizontal), ("countries",))

        ma = admin_site.site._registry[Product]
        self.assertIsInstance(ma, ProductAdmin)
        self.assertEqual(tuple(ma.list_display), ("name", "tier", "currency", "unit_price", "active"))
        self.assertEqual(tuple(ma.search_fields), ("name", "tier", "description"))
        self.assertEqual(tuple(ma.autocomplete_fields), ("currency",))
        self.assertEqual(tuple(ma.list_editable), ("active",))

        ma = admin_site.site._registry[Contact]
        self.assertIsInstance(ma, ContactAdmin)
        self.assertEqual(
            tuple(ma.search_fields),
            ("first_name", "last_name", "email", "phone", "organization__name"),
        )
        self.assertEqual(tuple(ma.autocomplete_fields), ("organization", "contact_type"))

        ma = admin_site.site._registry[OrganizationAddress]
        self.assertIsInstance(ma, OrganizationAddressAdmin)
        self.assertEqual(
            tuple(ma.search_fields),
            ("line1", "line2", "city", "state", "zip", "organization__name"),
        )
        self.assertEqual(tuple(ma.autocomplete_fields), ("organization", "country"))
        self.assertEqual(tuple(ma.list_editable), ("is_primary",))

        ma = admin_site.site._registry[OrderItem]
        self.assertIsInstance(ma, OrderItemAdmin)
        self.assertEqual(tuple(ma.search_fields), ("^order__order_number", "product__name"))
        self.assertEqual(tuple(ma.autocomplete_fields), ("order", "product"))
        self.assertIn("line_total_display", ma.readonly_fields)

        ma = admin_site.site._registry[Order]
        self.assertIsInstance(ma, OrderAdmin)
        from ourlives.admin import (
            ActiveCurrencyDropdownFilter,
            OrderProductFilter,
        )
        from project.admin_base import UsageBucketFilter, UsageMaxFilter, UsageMinFilter
        from unfold.contrib.filters.admin import (
            AutocompleteSelectFilter,
            FieldTextFilter,
            RangeDateTimeFilter,
        )

        self.assertEqual(
            tuple(ma.list_filter),
            (
                ("organization", AutocompleteSelectFilter),
                ("rep", AutocompleteSelectFilter),
                ("primary_contact", AutocompleteSelectFilter),
                ("invoice_contact", AutocompleteSelectFilter),
                OrderProductFilter,
                ("submitted_at", RangeDateTimeFilter),
                ("referral_organisation", FieldTextFilter),
                "order_types",
                "hcaptcha_verified",
                "is_upgrade_from_pilot",
                "is_referral_order",
                ("currency", ActiveCurrencyDropdownFilter),
                ("pilot_currency", ActiveCurrencyDropdownFilter),
                UsageBucketFilter,
                UsageMinFilter,
                UsageMaxFilter,
            ),
        )
        self.assertTrue(ma.list_filter_submit)
        self.assertEqual(
            tuple(ma.search_fields),
            ("^order_number", "^po_number", "organization__name", "rep__first_name", "rep__last_name", "rep__email", "primary_contact__last_name", "primary_contact__email", "invoice_contact__last_name", "invoice_contact__email", "referral_organisation"),
        )
        self.assertTrue(ma.search_help_text)
        self.assertEqual(tuple(ma.filter_horizontal), ("order_types",))
        self.assertEqual(
            tuple(ma.autocomplete_fields),
            ("organization", "rep", "primary_contact", "invoice_contact", "currency", "pilot_currency"),
        )
        self.assertEqual(ma.date_hierarchy, "submitted_at")
        self.assertIn("total_agreed_price_display", ma.readonly_fields)
        self.assertIn("is_pilot_order_display", ma.readonly_fields)
        self.assertEqual(len(ma.inlines), 1)

    def test_inline_classes_are_unfold(self):
        from unfold.admin import StackedInline as UnfoldStackedInline
        from unfold.admin import TabularInline as UnfoldTabularInline

        from ourlives.admin import (
            ContactInline,
            OrganizationAddressInline,
            OrderItemInline,
            OrgOrderInline,
        )

        self.assertTrue(issubclass(ContactInline, UnfoldStackedInline))
        self.assertTrue(issubclass(OrganizationAddressInline, UnfoldStackedInline))
        self.assertTrue(issubclass(OrderItemInline, UnfoldTabularInline))
        self.assertTrue(issubclass(OrgOrderInline, UnfoldTabularInline))
        self.assertEqual(ContactInline.extra, 0)
        self.assertEqual(OrganizationAddressInline.extra, 0)
        self.assertEqual(OrderItemInline.extra, 0)
        self.assertEqual(OrgOrderInline.extra, 0)
        self.assertFalse(OrgOrderInline.can_delete)
        self.assertFalse(OrgOrderInline.show_change_link)
        self.assertTrue(OrgOrderInline.hide_title)
        self.assertEqual(
            tuple(OrgOrderInline.fields),
            ("order_number_link", "number_of_scans", "submitted_at", "total_order_value_display", "order_link"),
        )
        self.assertEqual(
            tuple(OrgOrderInline.readonly_fields),
            ("order_number_link", "number_of_scans", "submitted_at", "total_order_value_display", "order_link"),
        )

        from django.contrib import admin as admin_site

        self.assertEqual(
            tuple(admin_site.site._registry[Organization].inlines),
            (OrgOrderInline, ContactInline, OrganizationAddressInline),
        )

    def test_order_link_display(self):
        from django.contrib import admin as admin_site

        from ourlives.admin import OrgOrderInline

        inline = OrgOrderInline(Order, admin_site.site)
        self.assertEqual(inline.order_link(None), "")
        self.assertEqual(inline.order_link(Order()), "")
        link = inline.order_link(Order(pk=999))
        self.assertIn("/admin/ourlives/order/999/change/", link)
        self.assertIn("inlinechangelink", link)
        self.assertIn(">Change<", link)

    def test_order_number_link_display(self):
        from django.contrib import admin as admin_site

        from ourlives.admin import OrgOrderInline

        inline = OrgOrderInline(Order, admin_site.site)
        self.assertEqual(inline.order_number_link(None), "")
        order = Order(pk=999, order_number="OL-42")
        link = inline.order_number_link(order)
        self.assertIn("/admin/ourlives/order/999/change/", link)
        self.assertIn("inlinechangelink", link)
        self.assertIn(">OL-42<", link)

    def test_total_order_value_display_readonly(self):
        from django.contrib import admin as admin_site

        from ourlives.admin import OrgOrderInline

        inline = OrgOrderInline(Order, admin_site.site)
        self.assertEqual(inline.total_order_value_display(None), "—")
        self.assertEqual(inline.total_order_value_display(Order()), "—")
        currency = Currency.objects.create(code="UVW", name="Test", exchange_rate=Decimal("1.00"))
        org = Organization.objects.create(name="Display Org")
        rep = Rep.objects.create(first_name="A", last_name="B", email="a@b.com")
        order = Order.objects.create(
            organization=org, rep=rep, po_number="PO-D", currency=currency,
            number_of_scans=10, cost_per_scan=Decimal("2.00"),
        )
        product = Product.objects.create(currency=currency, name="Widget", unit_price=Decimal("1.50"))
        OrderItem.objects.create(order=order, product=product, quantity=2, unit_price=Decimal("1.50"))
        self.assertEqual(inline.total_order_value_display(order), "UVW 23.00")

    def test_export_actions_inherited(self):
        from django.contrib import admin as admin_site

        for model in (Currency, Product, Contact, OrganizationAddress, Order, OrderItem):
            with self.subTest(model=model.__name__):
                ma = admin_site.site._registry[model]
                self.assertIn("export_selected", ma.actions)
                self.assertIn("export_all", getattr(ma, "actions_list", []))

    def test_child_models_registered_alongside_inlines(self):
        from django.contrib import admin as admin_site

        for model in (Contact, OrganizationAddress, OrderItem):
            with self.subTest(model=model.__name__):
                self.assertIn(model, admin_site.site._registry)
                self.assertEqual(
                    self.client.get(f"/admin/ourlives/{model._meta.model_name}/").status_code, 200,
                )

    def test_address_list_editable_toggle_persists(self):
        org = Organization.objects.create(name="Toggle Org")
        country = Country.objects.create(iso2="QX", iso3="QXX", name="Testland")
        address = OrganizationAddress.objects.create(
            organization=org, country=country,
            line1="1 Test St", city="Testville", zip="12345",
            is_primary=True,
        )
        self.client.post("/admin/ourlives/organizationaddress/", {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",
            "form-0-id": str(address.pk),
            "_save": "Save",
        })
        address.refresh_from_db()
        self.assertFalse(address.is_primary)

    def test_address_inline_toggle_via_organization_persists(self):
        org = Organization.objects.create(name="Toggle Org")
        country = Country.objects.create(iso2="QX", iso3="QXX", name="Testland")
        address = OrganizationAddress.objects.create(
            organization=org, country=country,
            line1="1 Test St", city="Testville", zip="12345",
            is_primary=True,
        )
        change_url = f"/admin/ourlives/organization/{org.pk}/change/"
        response = self.client.get(change_url)
        self.assertEqual(response.status_code, 200)
        prefixes = {
            fs.formset.prefix: fs
            for fs in response.context["inline_admin_formsets"]
        }
        self.assertEqual(set(prefixes), {"contacts", "addresses", "orders"})
        addr_prefix = next(
            prefix for prefix in prefixes
            if f"{prefix}-0-is_primary" in response.content.decode()
        )
        contact_prefix = next(p for p in prefixes if p not in (addr_prefix, "orders"))
        data = {
            "name": org.name,
            "description": "",
            "assigned_rep": "",
            f"{contact_prefix}-TOTAL_FORMS": "0",
            f"{contact_prefix}-INITIAL_FORMS": "0",
            f"{contact_prefix}-MIN_NUM_FORMS": "0",
            f"{contact_prefix}-MAX_NUM_FORMS": "1000",
            f"{addr_prefix}-TOTAL_FORMS": "1",
            f"{addr_prefix}-INITIAL_FORMS": "1",
            f"{addr_prefix}-MIN_NUM_FORMS": "0",
            f"{addr_prefix}-MAX_NUM_FORMS": "1000",
            f"{addr_prefix}-0-id": str(address.pk),
            f"{addr_prefix}-0-line1": address.line1,
            f"{addr_prefix}-0-line2": "",
            f"{addr_prefix}-0-city": address.city,
            f"{addr_prefix}-0-state": "",
            f"{addr_prefix}-0-zip": address.zip,
            f"{addr_prefix}-0-country": str(country.pk),
            "orders-TOTAL_FORMS": "0",
            "orders-INITIAL_FORMS": "0",
            "orders-MIN_NUM_FORMS": "0",
            "orders-MAX_NUM_FORMS": "1000",
            "_save": "Save",
        }
        response = self.client.post(change_url, data)
        self.assertEqual(response.status_code, 302)
        address.refresh_from_db()
        self.assertFalse(address.is_primary)


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class OrderAdminFilterTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("filter_admin", "f@test.com", "x")
        self.client = Client()
        self.client.force_login(self.admin)

        self.org_a = Organization.objects.create(name="Org A")
        self.org_b = Organization.objects.create(name="Org B")
        self.rep_a = Rep.objects.create(first_name="Ann", last_name="A", email="a@test.com")
        self.rep_b = Rep.objects.create(first_name="Bob", last_name="B", email="b@test.com")
        ct = ContactType.objects.create(code="billing", name="Billing")
        self.contact_p = Contact.objects.create(
            organization=self.org_a, contact_type=ct,
            first_name="Pam", last_name="Primary", email="pam@test.com",
        )
        self.contact_i = Contact.objects.create(
            organization=self.org_a, contact_type=ct,
            first_name="Ivan", last_name="Invoice", email="ivan@test.com",
        )
        self.contact_other = Contact.objects.create(
            organization=self.org_b, contact_type=ct,
            first_name="Olive", last_name="Other", email="olive@test.com",
        )
        self.usd = Currency.objects.create(code="USD", name="US Dollar", exchange_rate=Decimal("1.00"))
        self.eur = Currency.objects.create(code="EUR", name="Euro", exchange_rate=Decimal("0.92"))
        self.xxx = Currency.objects.create(
            code="XXX", name="Retired", exchange_rate=Decimal("1.00"), active=False,
        )
        self.prod_active = Product.objects.create(
            currency=self.usd, name="Active Widget", unit_price=Decimal("10.00"),
        )
        self.prod_legacy = Product.objects.create(
            currency=self.usd, name="Legacy Widget", unit_price=Decimal("5.00"), active=False,
        )
        self.order1 = Order.objects.create(
            organization=self.org_a, rep=self.rep_a, po_number="PO-1",
            primary_contact=self.contact_p, invoice_contact=self.contact_i,
            currency=self.usd, referral_organisation="Acme Holdings",
        )
        OrderItem.objects.create(
            order=self.order1, product=self.prod_active,
            quantity=1, unit_price=Decimal("10.00"),
        )
        OrderItem.objects.create(
            order=self.order1, product=self.prod_active,
            quantity=2, unit_price=Decimal("10.00"),
        )
        self.order2 = Order.objects.create(
            organization=self.org_b, rep=self.rep_b, po_number="PO-2",
            primary_contact=self.contact_other, currency=self.eur,
            pilot_currency=self.usd, referral_organisation="Beta Ltd",
        )
        OrderItem.objects.create(
            order=self.order2, product=self.prod_legacy,
            quantity=1, unit_price=Decimal("5.00"),
        )
        self.order3 = Order.objects.create(
            organization=self.org_a, rep=self.rep_b, po_number="PO-3",
        )

    def _changelist_pks(self, params):
        response = self.client.get("/admin/ourlives/order/", params)
        self.assertEqual(response.status_code, 200)
        return {o.pk for o in response.context["cl"].result_list}

    def test_filter_by_company(self):
        self.assertEqual(
            self._changelist_pks({"organization__id__exact": str(self.org_a.pk)}),
            {self.order1.pk, self.order3.pk},
        )

    def test_filter_by_rep(self):
        self.assertEqual(
            self._changelist_pks({"rep__id__exact": str(self.rep_b.pk)}),
            {self.order2.pk, self.order3.pk},
        )

    def test_contact_filters_are_independent_and_compose(self):
        self.assertEqual(
            self._changelist_pks({"primary_contact__id__exact": str(self.contact_p.pk)}),
            {self.order1.pk},
        )
        self.assertEqual(
            self._changelist_pks({"invoice_contact__id__exact": str(self.contact_i.pk)}),
            {self.order1.pk},
        )
        self.assertEqual(
            self._changelist_pks({
                "primary_contact__id__exact": str(self.contact_p.pk),
                "invoice_contact__id__exact": str(self.contact_other.pk),
            }),
            set(),
        )

    def test_filter_by_product_single_and_deduped(self):
        pks = self._changelist_pks({"product": str(self.prod_active.pk)})
        self.assertEqual(pks, {self.order1.pk})
        response = self.client.get("/admin/ourlives/order/", {"product": str(self.prod_active.pk)})
        self.assertEqual(len(response.context["cl"].result_list), 1)
        self.assertEqual(
            self._changelist_pks({"product": str(self.prod_legacy.pk)}),
            {self.order2.pk},
        )

    def test_product_lookups_include_inactive(self):
        from ourlives.admin import OrderProductFilter

        filt = OrderProductFilter(None, {}, Order, None)
        pks = {pk for pk, _label in filt.lookups(None, None)}
        self.assertIn(self.prod_active.pk, pks)
        self.assertIn(self.prod_legacy.pk, pks)

    def test_filter_by_submitted_range(self):
        wide = {
            "submitted_at_from_0": "2000-01-01", "submitted_at_from_1": "00:00:00",
            "submitted_at_to_0": "2100-01-01", "submitted_at_to_1": "00:00:00",
        }
        self.assertEqual(
            self._changelist_pks(wide),
            {self.order1.pk, self.order2.pk, self.order3.pk},
        )
        future = {
            "submitted_at_from_0": "2100-01-01", "submitted_at_from_1": "00:00:00",
            "submitted_at_to_0": "2101-01-01", "submitted_at_to_1": "00:00:00",
        }
        self.assertEqual(self._changelist_pks(future), set())

    def test_filter_by_referral_fragment(self):
        self.assertEqual(
            self._changelist_pks({"referral_organisation__icontains": "acme"}),
            {self.order1.pk},
        )

    def test_date_hierarchy_drills_down(self):
        year = str(self.order1.submitted_at.year)
        self.assertEqual(
            self._changelist_pks({"submitted_at__year": year}),
            {self.order1.pk, self.order2.pk, self.order3.pk},
        )
        self.assertEqual(self._changelist_pks({"submitted_at__year": "1999"}), set())

    def test_filter_by_currency_and_active_only_choices(self):
        self.assertEqual(
            self._changelist_pks({"currency__id__exact": str(self.usd.pk)}),
            {self.order1.pk},
        )
        self.assertEqual(
            self._changelist_pks({"currency__id__exact": str(self.eur.pk)}),
            {self.order2.pk},
        )
        self.assertEqual(
            self._changelist_pks({"pilot_currency__id__exact": str(self.usd.pk)}),
            {self.order2.pk},
        )
        from django.contrib import admin as admin_site

        from ourlives.admin import ActiveCurrencyDropdownFilter

        ma = admin_site.site._registry[Order]
        choices = ActiveCurrencyDropdownFilter.field_choices(
            None, Order._meta.get_field("currency"), None, ma,
        )
        self.assertEqual({pk for pk, _label in choices}, {self.usd.pk, self.eur.pk})

    def test_search_by_order_number(self):
        self.assertEqual(
            self._changelist_pks({"q": self.order1.order_number}),
            {self.order1.pk},
        )

    def test_billing_fieldset_on_change_page_only(self):
        from django.contrib import admin as admin_site

        from ourlives.admin import OrderAdmin

        ma = admin_site.site._registry[Order]
        self.assertIsInstance(ma, OrderAdmin)
        fieldsets = dict(ma.fieldsets)
        self.assertIn("Billing", fieldsets)
        billing_rows = fieldsets["Billing"]["fields"]
        billing_fields = [
            f for row in billing_rows for f in (row if isinstance(row, (tuple, list)) else (row,))
        ]
        self.assertEqual(
            set(billing_fields),
            {"invoice_sent", "invoice_sent_on", "invoice_paid",
             "invoice_paid_on", "commission_paid", "commission_paid_on",
             "rep_commission_note"},
        )
        self.assertEqual(
            billing_rows,
            (("invoice_sent", "invoice_sent_on"),
             ("invoice_paid", "invoice_paid_on"),
             ("commission_paid", "commission_paid_on"),
             "rep_commission_note"),
        )
        self.assertNotIn("rep_commission_note", ma.list_display)
        for field in billing_fields:
            self.assertNotIn(field, ma.list_display)
        response = self.client.get(f"/admin/ourlives/order/{self.order1.pk}/change/")
        self.assertEqual(response.status_code, 200)
        for field in billing_fields:
            self.assertContains(response, f'name="{field}"')
        changelist = self.client.get("/admin/ourlives/order/")
        self.assertEqual(changelist.status_code, 200)
        for field in billing_fields:
            self.assertNotContains(changelist, field)

    def test_totals_display_and_terms_fieldset(self):
        from django.contrib import admin as admin_site

        from ourlives.admin import OrderAdmin

        ma = admin_site.site._registry[Order]
        self.assertIsInstance(ma, OrderAdmin)
        self.assertIn("total_order_value_display", ma.list_display)
        self.assertNotIn("total_agreed_price_display", ma.list_display)
        terms = dict(ma.fieldsets)["Terms"]["fields"]
        self.assertIn("total_agreed_price_display", terms)
        self.assertIn("catalog_items_total_display", terms)
        self.assertIn("total_order_value_display", terms)

        self.order1.refresh_from_db()
        order = Order.objects.prefetch_related("items__product__currency").get(pk=self.order1.pk)
        self.assertEqual(ma.total_agreed_price_display(order), "—")
        self.assertEqual(ma.catalog_items_total_display(order), "USD 30.00")
        self.assertEqual(ma.total_order_value_display(order), "USD 30.00")
        self.assertEqual(ma.total_order_value_display(None), "—")

        response = self.client.get(f"/admin/ourlives/order/{self.order1.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Catalog items total")
        self.assertContains(response, "Total Order Value")


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class ChildInlineCoexistenceTests(TestCase):
    def setUp(self):
        call_command("base_loaddata")
        self.admin = User.objects.create_superuser("child_admin", "child@test.com", "x")
        self.client = Client()
        self.client.force_login(self.admin)

    def test_organization_change_renders_both_inlines(self):
        org = Organization.objects.create(name="Inline Org")
        contact_type = ContactType.objects.get(code="billing")
        Contact.objects.create(
            organization=org, contact_type=contact_type,
            first_name="Ada", last_name="Lovelace", email="ada@example.com",
        )
        response = self.client.get(f"/admin/ourlives/organization/{org.pk}/change/")
        self.assertEqual(response.status_code, 200)
        formsets = {
            fs.formset.prefix: fs
            for fs in response.context["inline_admin_formsets"]
        }
        self.assertEqual(set(formsets), {"contacts", "addresses", "orders"})
        self.assertEqual(
            [fs.formset.prefix for fs in response.context["inline_admin_formsets"]],
            ["orders", "contacts", "addresses"],
        )
        self.assertEqual(formsets["contacts"].formset.total_form_count(), 1)
        self.assertEqual(formsets["addresses"].formset.total_form_count(), 0)
        self.assertEqual(formsets["orders"].formset.total_form_count(), 0)

    def test_order_change_renders_items_inline(self):
        org = Organization.objects.create(name="Order Org")
        rep = Rep.objects.create(first_name="Jane", last_name="Doe", email="jane@ourlivesapp.com")
        currency = Currency.objects.create(code="TST", name="Test Dollar", exchange_rate=Decimal("1.00"))
        product = Product.objects.create(currency=currency, name="Scan", unit_price=Decimal("10.00"))
        order = Order.objects.create(organization=org, rep=rep, po_number="PO-1")
        OrderItem.objects.create(order=order, product=product, quantity=2, unit_price=Decimal("10.00"))
        response = self.client.get(f"/admin/ourlives/order/{order.pk}/change/")
        self.assertEqual(response.status_code, 200)
        formsets = {
            fs.formset.prefix: fs
            for fs in response.context["inline_admin_formsets"]
        }
        self.assertEqual(set(formsets), {"items"})
        self.assertEqual(formsets["items"].formset.total_form_count(), 1)


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class SidebarCoverageTests(TestCase):
    def _nav_links(self):
        from django.conf import settings as django_settings

        links = []

        def walk(items):
            for item in items:
                if item.get("link"):
                    links.append(str(item["link"]))
                walk(item.get("items", []))

        for group in django_settings.UNFOLD["SIDEBAR"]["navigation"]:
            walk(group["items"])
        return links

    def test_sidebar_not_showing_all_applications(self):
        from django.conf import settings as django_settings

        self.assertFalse(django_settings.UNFOLD["SIDEBAR"]["show_all_applications"])

    def test_every_registered_model_has_exactly_one_nav_entry(self):
        from django.contrib import admin as admin_site
        from django.urls import reverse

        links = self._nav_links()
        for model in admin_site.site._registry:
            with self.subTest(model=model._meta.label):
                if (
                    model._meta.app_label == "ourlives"
                    and model._meta.model_name == "appsettings"
                ):
                    url = reverse("admin:ourlives_appsettings_change")
                else:
                    url = reverse(
                        f"admin:{model._meta.app_label}_{model._meta.model_name}_changelist"
                    )
                self.assertEqual(links.count(url), 1)


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class SidebarPermissionTests(TestCase):
    def setUp(self):
        call_command("base_loaddata")
        self.client = Client()

    def _staff_with_perms(self, username, perms):
        user = User.objects.create_user(username, f"{username}@test.com", "x", is_staff=True)
        for perm in perms:
            app_label, codename = perm.split(".")
            user.user_permissions.add(
                Permission.objects.get(content_type__app_label=app_label, codename=codename)
            )
        return user

    def test_user_without_ourlives_perms_sees_no_ourlives_links(self):
        user = self._staff_with_perms("noperms", [])
        self.client.force_login(user)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"/admin/ourlives/", response.content)
        self.assertEqual(self.client.get("/admin/ourlives/order/").status_code, 403)

    def test_view_country_only_user_sees_only_countries(self):
        user = self._staff_with_perms("countryonly", ["ourlives.view_country"])
        self.client.force_login(user)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"/admin/ourlives/country/", response.content)
        self.assertNotIn(b"/admin/ourlives/order/", response.content)
        self.assertEqual(self.client.get("/admin/ourlives/country/").status_code, 200)
        self.assertEqual(self.client.get("/admin/ourlives/order/").status_code, 403)

    def test_cross_app_user_blocked_from_ourlives_exports(self):
        user = self._staff_with_perms("coreonly", ["core.view_brand"])
        self.client.force_login(user)
        response = self.client.post("/admin/ourlives/order/", {"action": "export_selected", "_selected_action": []})
        self.assertEqual(response.status_code, 403)


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class OrderSummaryModelTests(TestCase):
    def setUp(self):
        self.usd = Currency.objects.create(code="USD", name="US Dollar", exchange_rate=Decimal("1.00"))
        self.eur = Currency.objects.create(code="EUR", name="Euro", exchange_rate=Decimal("0.92"))
        self.gbp = Currency.objects.create(code="GBP", name="British Pound", exchange_rate=Decimal("0.75"))
        self.org = Organization.objects.create(name="Acme")
        self.rep = Rep.objects.create(first_name="Ann", last_name="A", email="a@test.com")
        self.pilot = OrderType.objects.create(code="pilot", name="Pilot Order")
        self.prod_usd = Product.objects.create(currency=self.usd, name="Widget", unit_price=Decimal("10.00"))
        self.prod_eur = Product.objects.create(currency=self.eur, name="Gadget", unit_price=Decimal("20.00"))
        self._n = 0

    def _order(self, org=None, rep=None, **kwargs):
        self._n += 1
        defaults = {"organization": org or self.org, "rep": rep or self.rep, "po_number": f"PO-{self._n}"}
        defaults.update(kwargs)
        return Order.objects.create(**defaults)

    def test_empty_records(self):
        for holder in (self.org, self.rep):
            with self.subTest(holder=holder):
                self.assertEqual(holder.order_count, 0)
                self.assertEqual(holder.agreed_scans_total, {})
                self.assertEqual(holder.catalog_items_total, {})
                self.assertEqual(holder.combined_total, {})
                self.assertIsNone(holder.last_order_date)

    def test_unsaved_instance(self):
        holder = Organization(name="Ghost")
        self.assertEqual(holder.order_count, 0)
        self.assertEqual(holder.agreed_scans_total, {})
        self.assertIsNone(holder.last_order_date)

    def test_agreed_nulls_as_zero_and_pilots_included(self):
        pilot_order = self._order(currency=self.usd, number_of_scans=500, cost_per_scan=Decimal("2.50"))
        pilot_order.order_types.add(self.pilot)
        self._order(currency=self.usd)  # null scans and cost
        self._order(currency=self.usd, number_of_scans=100)  # null cost
        self.assertEqual(self.org.agreed_scans_total, {"USD": Decimal("1250.00")})
        self.assertEqual(self.org.order_count, 3)

    def test_multi_currency_separation(self):
        self._order(currency=self.usd, number_of_scans=500, cost_per_scan=Decimal("3.50"))
        self._order(currency=self.eur, number_of_scans=100, cost_per_scan=Decimal("8.00"))
        self.assertEqual(
            self.org.agreed_scans_total, {"EUR": Decimal("800.00"), "USD": Decimal("1750.00")}
        )

    def test_agreed_currency_attribution(self):
        both = self._order(currency=self.usd, pilot_currency=self.gbp, number_of_scans=1, cost_per_scan=Decimal("10.00"))
        pilot_only = self._order(pilot_currency=self.gbp, number_of_scans=1, cost_per_scan=Decimal("20.00"))
        orphan = self._order(number_of_scans=1, cost_per_scan=Decimal("30.00"))
        totals = self.org.agreed_scans_total
        self.assertEqual(totals["USD"], Decimal("10.00"))
        self.assertEqual(totals["GBP"], Decimal("20.00"))
        self.assertEqual(totals[UNCATEGORIZED_CURRENCY], Decimal("30.00"))

    def test_items_attribution_order_first_then_product(self):
        order_usd = self._order(currency=self.usd)
        OrderItem.objects.create(order=order_usd, product=self.prod_eur, quantity=2, unit_price=Decimal("20.00"))
        self.assertEqual(self.org.catalog_items_total, {"USD": Decimal("40.00")})
        order_nocurrency = self._order()
        OrderItem.objects.create(order=order_nocurrency, product=self.prod_eur, quantity=1, unit_price=Decimal("20.00"))
        self.assertEqual(
            self.org.catalog_items_total, {"USD": Decimal("40.00"), "EUR": Decimal("20.00")}
        )

    def test_items_attribution_pilot_currency_middle(self):
        order = self._order(pilot_currency=self.gbp)
        OrderItem.objects.create(order=order, product=self.prod_eur, quantity=1, unit_price=Decimal("20.00"))
        self.assertEqual(self.org.catalog_items_total, {"GBP": Decimal("20.00")})

    def test_combined_total_per_currency(self):
        order = self._order(currency=self.usd, number_of_scans=500, cost_per_scan=Decimal("2.50"))
        OrderItem.objects.create(order=order, product=self.prod_usd, quantity=2, unit_price=Decimal("995.00"))
        other = self._order(currency=self.eur)
        OrderItem.objects.create(order=other, product=self.prod_eur, quantity=1, unit_price=Decimal("100.00"))
        self.assertEqual(
            self.org.combined_total, {"USD": Decimal("3240.00"), "EUR": Decimal("100.00")}
        )

    def test_last_order_date(self):
        first = self._order()
        second = self._order()
        self.assertEqual(self.org.last_order_date, max(first.submitted_at, second.submitted_at))
        self.assertEqual(self.rep.last_order_date, max(first.submitted_at, second.submitted_at))

    def test_rep_scope_is_direct_fk(self):
        other_rep = Rep.objects.create(first_name="Bob", last_name="B", email="b@test.com")
        self.org.assigned_rep = self.rep
        self.org.save()
        self._order(rep=other_rep, currency=self.usd, number_of_scans=10, cost_per_scan=Decimal("1.00"))
        self.assertEqual(self.rep.order_count, 0)
        self.assertEqual(self.rep.agreed_scans_total, {})
        self._order(rep=self.rep, currency=self.usd, number_of_scans=10, cost_per_scan=Decimal("1.00"))
        self.assertEqual(self.rep.order_count, 1)
        self.assertEqual(self.rep.agreed_scans_total, {"USD": Decimal("10.00")})

    def test_format_breakdown(self):
        self.assertEqual(format_currency_breakdown({}), "—")
        self.assertEqual(
            format_currency_breakdown({"USD": Decimal("1750"), "EUR": Decimal("800")}),
            "EUR 800.00 · USD 1,750.00",
        )

    def test_attach_money_breakdowns_matches_properties(self):
        order = self._order(currency=self.usd, number_of_scans=500, cost_per_scan=Decimal("2.50"))
        OrderItem.objects.create(order=order, product=self.prod_usd, quantity=1, unit_price=Decimal("10.00"))
        attach_money_breakdowns([self.org, self.rep])
        self.assertEqual(self.org._agreed_scans_total, self.org.agreed_scans_total)
        self.assertEqual(self.org._catalog_items_total, self.org.catalog_items_total)
        self.assertEqual(self.org._combined_total, self.org.combined_total)
        self.assertEqual(self.rep._agreed_scans_total, {"USD": Decimal("1250.00")})


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class OrderSummaryAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("summary_admin", "s@test.com", "x")
        self.client = Client()
        self.client.force_login(self.admin)
        self.usd = Currency.objects.create(code="USD", name="US Dollar", exchange_rate=Decimal("1.00"))
        self.eur = Currency.objects.create(code="EUR", name="Euro", exchange_rate=Decimal("0.92"))
        self.full = Organization.objects.create(name="Full Org")
        self.empty = Organization.objects.create(name="Empty Org")
        self.rep = Rep.objects.create(first_name="Ann", last_name="A", email="a@test.com")
        order = Order.objects.create(
            organization=self.full, rep=self.rep, po_number="PO-1",
            currency=self.usd, number_of_scans=500, cost_per_scan=Decimal("2.50"),
        )
        product = Product.objects.create(currency=self.usd, name="Widget", unit_price=Decimal("10.00"))
        OrderItem.objects.create(order=order, product=product, quantity=2, unit_price=Decimal("10.00"))
        Order.objects.create(organization=self.full, rep=self.rep, po_number="PO-2", currency=self.eur)

    def _changelist(self, model):
        response = self.client.get(f"/admin/ourlives/{model}/")
        self.assertEqual(response.status_code, 200)
        return response

    def test_changelists_render_breakdowns(self):
        content = self._changelist("rep").content.decode()
        for text in ("Agreed scans total", "Catalog items total", "Total Order Value", "USD 1,250.00"):
            self.assertIn(text, content)

    def test_organization_changelist_is_slim(self):
        from django.contrib import admin
        ma = admin.site._registry[Organization]
        self.assertEqual(
            tuple(ma.list_display),
            ("name", "order_count_display", "rep_link", "last_order_date_display", "usage_pct_display", "combined_total_display"),
        )
        content = self._changelist("organization").content.decode()
        for text in ("Orders", "Rep", "Last order", "Total Order Value", "Usage %", "—"):
            self.assertIn(text, content)
        for text in ("Agreed scans total", "Catalog items total"):
            self.assertNotIn(text, content)

    def test_organization_rep_link_and_usage_pct(self):
        from django.contrib import admin

        from ourlives.models import annotate_organization_usage

        ma = admin.site._registry[Organization]
        rep = Rep.objects.create(first_name="Bob", last_name="Jones", email="bob@test.com")
        org = Organization.objects.create(name="Linked Org", assigned_rep=rep)
        linked = ma.rep_link(org)
        self.assertIn(f"/admin/ourlives/rep/{rep.pk}/change/", linked)
        self.assertIn("Bob Jones", linked)
        self.assertEqual(ma.rep_link(self.empty), "—")
        self.assertEqual(ma.rep_link(None), "—")
        # Real annotated Usage % from UsageStatsAdminMixin (no dummy).
        self.assertEqual(ma.usage_pct_display(org), "—")
        self.assertEqual(ma.usage_pct_display(None), "—")
        project = Project.objects.create(name="Usage Project")
        AppSettings.get_solo()
        AppSettings.objects.update(total_tokens=10_000)
        InvitationCode.objects.create(project=project, organization=org, code="U-50", max_use=10, current_use=5)
        annotated = annotate_organization_usage(Organization.objects.filter(pk=org.pk)).get()
        self.assertEqual(ma.usage_pct_display(annotated), "50%")

    def test_changelist_annotations_match_properties(self):
        for model in ("organization", "rep"):
            with self.subTest(model=model):
                for obj in self._changelist(model).context["cl"].result_list:
                    self.assertEqual(obj._order_count, obj.order_count)
                    self.assertEqual(obj._last_order_date, obj.last_order_date)
                    self.assertEqual(obj._agreed_scans_total, obj.agreed_scans_total)
                    self.assertEqual(obj._combined_total, obj.combined_total)

    def _ordering_idx(self, model, column):
        # `o` indexes cl.list_display, which prepends the action checkbox
        cl = self.client.get(f"/admin/ourlives/{model}/").context["cl"]
        return list(cl.list_display).index(column)

    def test_sorting_by_count_and_date(self):
        for model in ("organization", "rep"):
            for column in ("order_count_display", "last_order_date_display"):
                idx = self._ordering_idx(model, column)
                with self.subTest(model=model, column=column):
                    for prefix in ("", "-"):
                        response = self.client.get(f"/admin/ourlives/{model}/", {"o": f"{prefix}{idx}"})
                        self.assertEqual(response.status_code, 200)
        # self.full has the most orders of any org (a backfill org also exists)
        idx = self._ordering_idx("organization", "order_count_display")
        response = self.client.get("/admin/ourlives/organization/", {"o": f"-{idx}"})
        pks = [o.pk for o in response.context["cl"].result_list]
        self.assertEqual(pks[0], self.full.pk)
        self.assertEqual(set(pks), set(Organization.objects.values_list("pk", flat=True)))

    def test_no_per_row_queries(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as before:
            self.client.get("/admin/ourlives/organization/")
        for i in range(3):
            org = Organization.objects.create(name=f"Extra {i}")
            Order.objects.create(organization=org, rep=self.rep, po_number=f"PO-X{i}", currency=self.usd)
        with CaptureQueriesContext(connection) as after:
            self.client.get("/admin/ourlives/organization/")
        self.assertEqual(len(before), len(after))

    def test_change_forms_show_summary_section(self):
        for url in (f"/admin/ourlives/organization/{self.full.pk}/change/",
                    f"/admin/ourlives/rep/{self.rep.pk}/change/"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                content = response.content.decode()
                for text in ("Order summary", "price frozen at order time",
                             "never added together", "USD 1,250.00"):
                    self.assertIn(text, content)

    def test_empty_change_form_placeholders(self):
        content = self.client.get(f"/admin/ourlives/organization/{self.empty.pk}/change/").content.decode()
        self.assertIn("Order summary", content)
        self.assertIn("—", content)

    def test_add_forms_render(self):
        for url in ("/admin/ourlives/organization/add/", "/admin/ourlives/rep/add/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class CrossLinkedChangeViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("xlink_admin", "x@test.com", "x")
        self.client = Client()
        self.client.force_login(self.admin)
        self.org = Organization.objects.create(name="Acme", description="d")
        self.rep = Rep.objects.create(
            first_name="Rita", last_name="Rep", email="rita@test.com",
        )
        self.org.assigned_rep = self.rep
        self.org.save()
        self.ct = ContactType.objects.create(code="billing", name="Billing")
        self.primary = Contact.objects.create(
            organization=self.org, contact_type=self.ct,
            first_name="Pam", last_name="Primary", email="pam@test.com", phone="111",
        )
        self.invoice = Contact.objects.create(
            organization=self.org, contact_type=self.ct,
            first_name="Ivan", last_name="Invoice", email="ivan@test.com", phone="222",
        )
        self.order = Order.objects.create(
            organization=self.org, rep=self.rep, po_number="PO-1",
            primary_contact=self.primary, invoice_contact=self.invoice,
        )
        self.project = Project.objects.create(name="Proj")
        AppSettings.get_solo()
        AppSettings.objects.update(total_tokens=10000)
        self.code_type = CodeType.objects.create(code="up_to_5", name="Up to 5", max_codes=5)
        self.code = InvitationCode.objects.create(
            project=self.project, organization=self.org, max_use=10,
            order=self.order, code_type=self.code_type,
        )

    def test_company_change_lists_orders(self):
        self.order.number_of_scans = 500
        self.order.save()
        response = self.client.get(f"/admin/ourlives/organization/{self.org.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_number)
        self.assertContains(
            response, reverse("admin:ourlives_order_change", args=[self.order.pk]),
        )
        self.assertContains(response, "Total: 500 scans across 1 order")
        self.assertNotContains(response, "View all 1 order")
        self.assertContains(response, "inlinechangelink")
        self.assertContains(response, ">Change<")

    def test_order_link_view_label_without_change_permission(self):
        viewer = User.objects.create_user("order_viewer", "v@test.com", "x", is_staff=True)
        for codename in ("view_organization", "change_organization", "view_order"):
            viewer.user_permissions.add(Permission.objects.get(codename=codename))
        self.client.force_login(viewer)
        response = self.client.get(f"/admin/ourlives/organization/{self.org.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "inlineviewlink")
        self.assertContains(response, ">View<")
        self.assertNotContains(response, "inlinechangelink")

    def test_company_add_view_renders(self):
        self.assertEqual(self.client.get("/admin/ourlives/organization/add/").status_code, 200)

    def test_company_orders_inline_lists_all_with_total(self):
        for i in range(25):
            Order.objects.create(
                organization=self.org, rep=self.rep, po_number=f"PO-P{i}",
                number_of_scans=10,
            )
        response = self.client.get(f"/admin/ourlives/organization/{self.org.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Total: 250 scans across 26 orders")
        last_number = self.org.orders.order_by("order_number").last().order_number
        self.assertContains(response, last_number)

    def test_rep_lists_paginate_independently(self):
        for i in range(25):
            Organization.objects.create(name=f"Co {i:02d}", assigned_rep=self.rep)
        response = self.client.get(
            f"/admin/ourlives/rep/{self.rep.pk}/change/",
            {"rep_companies_page": 2},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 2 of 2")
        self.assertContains(response, self.order.order_number)
        self.assertContains(response, "View all 1 order")

    def test_rep_change_lists_companies_and_orders(self):
        response = self.client.get(f"/admin/ourlives/rep/{self.rep.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acme")
        self.assertContains(
            response,
            reverse("admin:ourlives_organization_change", args=[self.org.pk]),
        )
        self.assertContains(response, self.order.order_number)
        self.assertContains(
            response, reverse("admin:ourlives_order_change", args=[self.order.pk]),
        )

    def test_order_change_shows_rep_card_contacts_and_codes(self):
        response = self.client.get(f"/admin/ourlives/order/{self.order.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "mailto:rita@test.com")
        self.assertContains(response, "Open rep")
        self.assertContains(response, "(primary)")
        self.assertContains(response, "(invoice)")
        self.assertContains(
            response,
            reverse("admin:ourlives_contact_change", args=[self.primary.pk]),
        )
        self.assertContains(response, self.code.code)
        self.assertContains(
            response,
            reverse("admin:ourlives_invitationcode_change", args=[self.code.pk]),
        )
        self.assertContains(response, "Related")

    def test_company_change_lists_codes_across_orders_and_direct(self):
        orderless = InvitationCode.objects.create(
            project=self.project, organization=self.org, max_use=4,
        )
        other_org = Organization.objects.create(name="Other")
        other_order = Order.objects.create(
            organization=other_org, rep=self.rep, po_number="PO-9",
        )
        other_code = InvitationCode.objects.create(
            project=self.project, organization=other_org, max_use=3,
            order=other_order, code_type=self.code_type,
        )
        response = self.client.get(f"/admin/ourlives/organization/{self.org.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Codes across orders")
        self.assertContains(response, "Codes (direct)")
        self.assertContains(response, self.code.code)
        self.assertContains(response, orderless.code)
        self.assertNotContains(response, other_code.code)
        self.assertContains(
            response,
            reverse("admin:ourlives_invitationcode_change", args=[self.code.pk]),
        )
        self.assertContains(response, f"order__organization__id__exact={self.org.pk}")
        self.assertContains(response, f"organization__id__exact={self.org.pk}")

    def test_company_codes_paginate_and_invalid_page(self):
        for i in range(25):
            InvitationCode.objects.create(
                project=self.project, organization=self.org, max_use=2,
                order=self.order,
            )
        response = self.client.get(
            f"/admin/ourlives/organization/{self.org.pk}/change/",
            {"org_order_codes_page": 2},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Page 2 of 2")
        bogus = self.client.get(
            f"/admin/ourlives/organization/{self.org.pk}/change/",
            {"org_order_codes_page": "bogus"},
        )
        self.assertEqual(bogus.status_code, 200)
        self.assertContains(bogus, "Page 1 of 2")

    def test_order_change_shows_company_card(self):
        response = self.client.get(f"/admin/ourlives/order/{self.order.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Open company")
        self.assertContains(
            response,
            reverse("admin:ourlives_organization_change", args=[self.org.pk]),
        )
        self.assertContains(response, "2 contacts")
        self.assertContains(response, "1 order")
        self.assertContains(response, "1 code")

    def test_company_card_address_fallback(self):
        country = Country.objects.create(iso2="ZZ", iso3="ZZZ", name="Zedland")
        OrganizationAddress.objects.create(
            organization=self.org, country=country,
            line1="Main 1", city="Springfield", zip="1",
        )
        response = self.client.get(f"/admin/ourlives/order/{self.order.pk}/change/")
        self.assertContains(response, "Main 1, Springfield")
        OrganizationAddress.objects.create(
            organization=self.org, country=country,
            line1="Prime 9", city="Shelbyville", zip="2", is_primary=True,
        )
        response = self.client.get(f"/admin/ourlives/order/{self.order.pk}/change/")
        self.assertContains(response, "Prime 9, Shelbyville")

    def test_restricted_user_sees_code_counts_and_restricted_card(self):
        user = User.objects.create_user("codes_restricted", "c@test.com", "x", is_staff=True)
        for codename in ("view_organization", "change_organization"):
            user.user_permissions.add(Permission.objects.get(codename=codename))
        self.client.force_login(user)
        response = self.client.get(f"/admin/ourlives/organization/{self.org.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1 code")
        self.assertNotContains(
            response, reverse("admin:ourlives_invitationcode_change", args=[self.code.pk]),
        )
        user2 = User.objects.create_user("card_restricted", "d@test.com", "x", is_staff=True)
        for codename in ("view_order", "change_order"):
            user2.user_permissions.add(Permission.objects.get(codename=codename))
        self.client.force_login(user2)
        response = self.client.get(f"/admin/ourlives/order/{self.order.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "(details restricted)")
        self.assertNotContains(
            response, reverse("admin:ourlives_organization_change", args=[self.org.pk]),
        )

    def test_restricted_user_sees_counts_not_links(self):
        from django.contrib import admin as admin_site

        user = User.objects.create_user("restricted", "r@test.com", "x", is_staff=True)
        for codename in ("view_organization", "change_organization"):
            user.user_permissions.add(Permission.objects.get(codename=codename))
        self.client.force_login(user)
        response = self.client.get(f"/admin/ourlives/organization/{self.org.pk}/change/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "1 order")
        self.assertNotContains(
            response, reverse("admin:ourlives_order_change", args=[self.order.pk]),
        )
        ma = admin_site.site._registry[Organization]
        self.assertEqual(ma.total_scans_display(Organization(name="unsaved")), "—")

    def test_empty_states(self):
        bare_org = Organization.objects.create(name="Bare")
        response = self.client.get(f"/admin/ourlives/organization/{bare_org.pk}/change/")
        self.assertContains(response, "No orders yet")
        bare_rep = Rep.objects.create(first_name="Bo", last_name="Re", email="bo@test.com")
        response = self.client.get(f"/admin/ourlives/rep/{bare_rep.pk}/change/")
        self.assertContains(response, "No companies yet")
        self.assertContains(response, "No orders yet")
        bare_order = Order.objects.create(
            organization=bare_org, rep=bare_rep, po_number="PO-BARE",
        )
        response = self.client.get(f"/admin/ourlives/order/{bare_order.pk}/change/")
        self.assertContains(response, "No contacts yet")
        self.assertContains(response, "No codes yet")
