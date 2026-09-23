from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from ourlives.models import (
    AppSettings,
    InvitationCode,
    Order,
    Organization,
    Project,
    Rep,
    annotate_code_usage,
    annotate_order_usage,
    annotate_organization_usage,
)


class UsageStatsFixtureMixin(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Usage Project")
        self.org = Organization.objects.create(name="Usage Org")
        self.other_org = Organization.objects.create(name="Other Org")
        self.rep = Rep.objects.create(first_name="Jane", last_name="Doe", email="jane@usage.test")
        AppSettings.get_solo()
        AppSettings.objects.update(total_tokens=10_000)

    def make_code(self, org, used, max_use, order=None, code="C"):
        import uuid

        return InvitationCode.objects.create(
            project=self.project,
            organization=org,
            order=order,
            code=f"{code}-{uuid.uuid4().hex[:6]}",
            max_use=max_use,
            current_use=used,
        )

    def make_order(self, org, number):
        return Order.objects.create(
            order_number=number,
            organization=org,
            rep=self.rep,
            po_number=f"PO-{number}",
        )


class CodeUsageExpressionTests(UsageStatsFixtureMixin):
    def test_normal_percentage(self):
        code = self.make_code(self.org, used=3, max_use=10)
        annotated = annotate_code_usage(InvitationCode.objects.filter(pk=code.pk)).get()
        self.assertAlmostEqual(annotated._usage_pct, 30.0)

    def test_zero_quota_is_null(self):
        code = self.make_code(self.org, used=0, max_use=0)
        annotated = annotate_code_usage(InvitationCode.objects.filter(pk=code.pk)).get()
        self.assertIsNone(annotated._usage_pct)


class OrderUsageTests(UsageStatsFixtureMixin):
    def test_token_weighted_math(self):
        order = self.make_order(self.org, "OL-USAGE-1")
        self.make_code(self.org, used=4, max_use=10, order=order)
        self.make_code(self.org, used=6, max_use=10, order=order)
        annotated = annotate_order_usage(Order.objects.filter(pk=order.pk)).get()
        self.assertEqual(annotated._codes_used, 10)
        self.assertEqual(annotated._codes_max, 20)
        self.assertAlmostEqual(annotated._usage_pct, 50.0)

    def test_codeless_order_is_null(self):
        order = self.make_order(self.org, "OL-USAGE-2")
        annotated = annotate_order_usage(Order.objects.filter(pk=order.pk)).get()
        self.assertIsNone(annotated._usage_pct)


class OrganizationUsageTests(UsageStatsFixtureMixin):
    def test_direct_only(self):
        self.make_code(self.org, used=5, max_use=10)
        annotated = annotate_organization_usage(Organization.objects.filter(pk=self.org.pk)).get()
        self.assertAlmostEqual(annotated._usage_pct, 50.0)

    def test_combined_direct_and_order_codes(self):
        order = self.make_order(self.org, "OL-USAGE-3")
        self.make_code(self.org, used=4, max_use=10)  # direct
        self.make_code(self.org, used=6, max_use=10, order=order)  # via order
        annotated = annotate_organization_usage(Organization.objects.filter(pk=self.org.pk)).get()
        self.assertEqual(annotated._codes_used, 10)
        self.assertEqual(annotated._codes_max, 20)
        self.assertAlmostEqual(annotated._usage_pct, 50.0)

    def test_dually_linked_code_counted_once(self):
        order = self.make_order(self.org, "OL-USAGE-4")
        self.make_code(self.org, used=5, max_use=10, order=order)
        annotated = annotate_organization_usage(Organization.objects.filter(pk=self.org.pk)).get()
        self.assertEqual(annotated._codes_used, 5)
        self.assertEqual(annotated._codes_max, 10)
        self.assertAlmostEqual(annotated._usage_pct, 50.0)

    def test_empty_org_is_null(self):
        annotated = annotate_organization_usage(Organization.objects.filter(pk=self.other_org.pk)).get()
        self.assertIsNone(annotated._usage_pct)


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class UsageAdminTests(UsageStatsFixtureMixin):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser("usage-admin", "a@usage.test", "pw")
        self.client.force_login(self.admin)
        self.low_order = self.make_order(self.org, "OL-ADM-1")
        self.low_code = self.make_code(self.org, used=1, max_use=10, order=self.low_order)
        self.high_order = self.make_order(self.org, "OL-ADM-2")
        self.high_code = self.make_code(self.org, used=9, max_use=10, order=self.high_order)

    def result_pks(self, response):
        return [obj.pk for obj in response.context["cl"].result_list]

    def test_code_sort_ascending_nulls_last(self):
        zero = self.make_code(self.org, used=0, max_use=0)
        response = self.client.get("/admin/ourlives/invitationcode/?o=7")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.result_pks(response)[-1], zero.pk)
        self.assertLess(
            self.result_pks(response).index(self.low_code.pk),
            self.result_pks(response).index(self.high_code.pk),
        )

    def test_code_sort_descending_nulls_last(self):
        zero = self.make_code(self.org, used=0, max_use=0)
        response = self.client.get("/admin/ourlives/invitationcode/?o=-7")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.result_pks(response)[-1], zero.pk)
        self.assertLess(
            self.result_pks(response).index(self.high_code.pk),
            self.result_pks(response).index(self.low_code.pk),
        )

    def test_bucket_filter(self):
        response = self.client.get("/admin/ourlives/invitationcode/?usage_bucket=warning")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.result_pks(response), [self.high_code.pk])

    def test_threshold_combo(self):
        response = self.client.get("/admin/ourlives/invitationcode/?usage_min=90&usage_max=100")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.result_pks(response), [self.high_code.pk])

    def test_order_sort_and_filter(self):
        response = self.client.get("/admin/ourlives/order/?o=-9")
        self.assertEqual(response.status_code, 200)
        self.assertLess(
            self.result_pks(response).index(self.high_order.pk),
            self.result_pks(response).index(self.low_order.pk),
        )
        response = self.client.get("/admin/ourlives/order/?usage_bucket=warning")
        self.assertEqual(self.result_pks(response), [self.high_order.pk])

    def test_order_sort_ascending_nulls_last(self):
        empty_order = self.make_order(self.org, "OL-ADM-3")
        response = self.client.get("/admin/ourlives/order/?o=9")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.result_pks(response)[-1], empty_order.pk)

    def test_organization_sort_and_filter(self):
        response = self.client.get("/admin/ourlives/organization/?o=-8")
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.org.pk, self.result_pks(response))

    def test_organization_sort_ascending_nulls_last(self):
        response = self.client.get("/admin/ourlives/organization/?o=8")
        self.assertEqual(response.status_code, 200)
        # Empty orgs (Legacy from migration 0005 + other_org) sort last.
        legacy = Organization.objects.get(name="Legacy")
        pks = self.result_pks(response)
        self.assertEqual(pks[0], self.org.pk)
        self.assertCountEqual(pks[-2:], [legacy.pk, self.other_org.pk])

    def test_organization_bucket_filter(self):
        # Combined org usage is (1+9)/(10+10) = 50% -> "half" bucket.
        response = self.client.get("/admin/ourlives/organization/?usage_bucket=half")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.result_pks(response), [self.org.pk])
        response = self.client.get("/admin/ourlives/organization/?usage_bucket=noquota")
        legacy = Organization.objects.get(name="Legacy")  # data migration 0005
        self.assertCountEqual(self.result_pks(response), [self.other_org.pk, legacy.pk])
