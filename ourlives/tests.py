import json
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.test import TestCase, Client
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
    calculate_token_count,
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

    def test_currency_delete_sets_null(self):
        currency = Currency.objects.create(code="USD", name="US Dollar", exchange_rate=Decimal("1.00"))
        order = self._create_order(currency=currency, pilot_currency=currency)
        currency.delete()
        order.refresh_from_db()
        self.assertIsNone(order.currency)
        self.assertIsNone(order.pilot_currency)


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
        self.assertEqual(tuple(ma.search_fields), ("code", "name"))
        self.assertEqual(tuple(ma.list_editable), ("active",))
        self.assertEqual(tuple(ma.filter_horizontal), ("countries",))

        ma = admin_site.site._registry[Product]
        self.assertIsInstance(ma, ProductAdmin)
        self.assertEqual(tuple(ma.list_display), ("name", "tier", "currency", "unit_price", "active"))
        self.assertEqual(tuple(ma.autocomplete_fields), ("currency",))
        self.assertEqual(tuple(ma.list_editable), ("active",))

        ma = admin_site.site._registry[Contact]
        self.assertIsInstance(ma, ContactAdmin)
        self.assertEqual(tuple(ma.autocomplete_fields), ("organization", "contact_type"))

        ma = admin_site.site._registry[OrganizationAddress]
        self.assertIsInstance(ma, OrganizationAddressAdmin)
        self.assertEqual(tuple(ma.autocomplete_fields), ("organization", "country"))
        self.assertEqual(tuple(ma.list_editable), ("is_primary",))

        ma = admin_site.site._registry[OrderItem]
        self.assertIsInstance(ma, OrderItemAdmin)
        self.assertEqual(tuple(ma.autocomplete_fields), ("order", "product"))
        self.assertIn("line_total_display", ma.readonly_fields)

        ma = admin_site.site._registry[Order]
        self.assertIsInstance(ma, OrderAdmin)
        self.assertEqual(tuple(ma.filter_horizontal), ("order_types",))
        self.assertEqual(ma.date_hierarchy, "submitted_at")
        self.assertIn("total_agreed_price_display", ma.readonly_fields)
        self.assertIn("is_pilot_order_display", ma.readonly_fields)
        self.assertEqual(len(ma.inlines), 1)

    def test_export_actions_inherited(self):
        from django.contrib import admin as admin_site

        for model in (Currency, Product, Contact, OrganizationAddress, Order, OrderItem):
            with self.subTest(model=model.__name__):
                ma = admin_site.site._registry[model]
                self.assertIn("export_selected", ma.actions)
                self.assertIn("export_all", getattr(ma, "actions_list", []))

    def test_address_inline_is_primary_toggle_persists(self):
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
