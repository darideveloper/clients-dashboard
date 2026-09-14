import re

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from ourlives.models import (
    AppSettings,
    Contact,
    Country,
    InvitationCode,
    Order,
    OrderItem,
    Organization,
    Rep,
)

EMAIL_RX = re.compile(r"^test-[0-9a-f]+@gmail\.com$")


def seed(**kwargs):
    params = {"seed": 42, "reps": 6, "orgs": 10, "orders": 25}
    params.update(kwargs)
    call_command("seed_ourlives_demo", **params)


class SeedDemoCommandTests(TestCase):
    def test_canonical_run_creates_expected_volumes(self):
        seed()
        self.assertEqual(
            Rep.objects.filter(email__startswith="test-").count(), 6)
        self.assertEqual(
            Organization.objects.filter(name__startswith="Demo ").count(), 10)
        self.assertEqual(Order.objects.count(), 25)
        self.assertGreater(OrderItem.objects.count(), 0)
        self.assertGreater(InvitationCode.objects.count(), 0)

    def test_all_emails_use_test_domain_and_are_unique(self):
        seed()
        emails = ([r.email for r in Rep.objects.all()]
                  + [c.email for c in Contact.objects.all()])
        self.assertGreater(len(emails), 0)
        for email in emails:
            self.assertRegex(email, EMAIL_RX)
        self.assertEqual(len(set(emails)), len(emails))

    def test_lookups_untouched_and_clear_rerun_has_no_dupes(self):
        seed()
        seed(clear=True)
        self.assertEqual(Country.objects.count(), 249)
        self.assertEqual(
            Organization.objects.filter(name__startswith="Demo ").count(), 10)
        self.assertEqual(
            Organization.objects.filter(name="Demo Empty Org").count(), 1)

    def test_clear_preserves_handmade_rows(self):
        rep = Rep.objects.create(first_name="Real", last_name="Person",
                                 email="real@company.com")
        org = Organization.objects.create(name="Real Org", assigned_rep=rep)
        seed(clear=True)
        self.assertTrue(Rep.objects.filter(pk=rep.pk).exists())
        self.assertTrue(Organization.objects.filter(pk=org.pk).exists())

    def test_calculated_field_branches_exist(self):
        seed()
        self.assertTrue(Order.objects.filter(
            number_of_scans__isnull=True).exists())
        self.assertTrue(Order.objects.filter(
            cost_per_scan__isnull=True).exists())
        self.assertTrue(Order.objects.filter(
            currency__isnull=True, pilot_currency__isnull=True,
            number_of_scans__isnull=False).exists())
        self.assertTrue(Order.objects.filter(
            order_types__isnull=True).exists())
        self.assertTrue(Order.objects.filter(
            order_types__code="pilot").exists())
        self.assertTrue(InvitationCode.objects.filter(
            is_active=False).exists())
        self.assertTrue(InvitationCode.objects.filter(
            current_use__gt=0).exists())
        full = [o for o in Organization.objects.filter(
            name__startswith="Demo ") if "Uncategorized" in o.combined_total]
        self.assertTrue(full, "no org shows an Uncategorized combined total")
        empty = Organization.objects.get(name="Demo Empty Org")
        self.assertEqual(empty.order_count, 0)
        self.assertIsNone(empty.last_order_date)
        full_org = Organization.objects.get(name="Demo Full Org")
        most = max(o.order_count for o in Organization.objects.all())
        self.assertEqual(full_org.order_count, most)
        self.assertGreater(full_org.order_count, 0)
        settings = AppSettings.get_solo()
        self.assertLessEqual(settings.tokens_assigned, settings.total_tokens)

    def test_token_pool_consistent(self):
        seed()
        settings = AppSettings.get_solo()
        self.assertEqual(settings.tokens_available,
                         settings.total_tokens - settings.tokens_assigned)


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class SeedDemoAdminTests(TestCase):
    def test_admin_pages_render_with_demo_data(self):
        seed()
        admin = User.objects.create_superuser("demo_admin", "d@test.com", "x")
        client = Client()
        client.force_login(admin)
        for url in ("organization", "rep", "order", "invitationcode"):
            with self.subTest(url=url):
                self.assertEqual(
                    client.get(f"/admin/ourlives/{url}/").status_code, 200)
        org = Organization.objects.get(name="Demo Full Org")
        self.assertEqual(
            client.get(f"/admin/ourlives/organization/{org.pk}/change/").status_code, 200)
        order = Order.objects.filter(items__isnull=False).first()
        self.assertEqual(
            client.get(f"/admin/ourlives/order/{order.pk}/change/").status_code, 200)
