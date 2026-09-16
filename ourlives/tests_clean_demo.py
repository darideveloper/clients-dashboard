import sys
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from ourlives.models import (
    Contact,
    Country,
    InvitationCode,
    Order,
    OrderItem,
    Organization,
    OrganizationAddress,
    Project,
    Rep,
)


def seed_demo(**kwargs):
    params = {"seed": 42, "reps": 6, "orgs": 10, "orders": 25}
    params.update(kwargs)
    call_command("seed_ourlives_demo", **params)


def demo_counts():
    return {
        "orgs": Organization.objects.filter(name__startswith="Demo ").count(),
        "projects": Project.objects.filter(name__startswith="Demo ").count(),
        "reps": Rep.objects.filter(email__startswith="test-").count(),
        "contacts": Contact.objects.filter(
            organization__name__startswith="Demo ").count(),
        "addresses": OrganizationAddress.objects.filter(
            organization__name__startswith="Demo ").count(),
        "orders": Order.objects.filter(
            organization__name__startswith="Demo ").count(),
        "items": OrderItem.objects.filter(
            order__organization__name__startswith="Demo ").count(),
        "codes": InvitationCode.objects.filter(
            organization__name__startswith="Demo ").count(),
    }


def interactive(*answers):
    """Patch stdin/input for one interactive clean run."""
    return (mock.patch.object(sys.stdin, "isatty", return_value=True),
            mock.patch("builtins.input", side_effect=list(answers)))


class CleanDemoCommandTests(TestCase):
    def test_dry_run_deletes_nothing(self):
        seed_demo()
        before = demo_counts()
        self.assertGreater(before["orgs"], 0)
        call_command("clean_ourlives_demo", dry_run=True)
        self.assertEqual(demo_counts(), before)
        self.assertEqual(Country.objects.count(), 249)

    def test_yes_deletes_all_demo_scope_but_keeps_handmade(self):
        rep = Rep.objects.create(first_name="Real", last_name="Person",
                                 email="real@company.com")
        org = Organization.objects.create(name="Real Org", assigned_rep=rep)
        seed_demo()
        call_command("clean_ourlives_demo", yes=True)
        self.assertEqual(demo_counts(), {k: 0 for k in demo_counts()})
        self.assertTrue(Rep.objects.filter(pk=rep.pk).exists())
        self.assertTrue(Organization.objects.filter(pk=org.pk).exists())
        self.assertEqual(Country.objects.count(), 249)

    def test_keep_all_answers_delete_nothing(self):
        seed_demo()
        before = demo_counts()
        tty, fake_input = interactive(*["k"] * 40)
        with tty, fake_input:
            call_command("clean_ourlives_demo")
        self.assertEqual(demo_counts(), before)

    def test_delete_first_org_only(self):
        seed_demo()
        first = Organization.objects.filter(
            name__startswith="Demo ").order_by("name").first()
        tty, fake_input = interactive("d", *(["k"] * 40))
        with tty, fake_input:
            call_command("clean_ourlives_demo")
        self.assertFalse(Organization.objects.filter(pk=first.pk).exists())
        self.assertEqual(demo_counts()["orgs"], 9)
        self.assertFalse(Order.objects.filter(organization=first).exists())
        self.assertFalse(InvitationCode.objects.filter(
            organization=first).exists())

    def test_quit_keeps_rest_unprompted(self):
        seed_demo()
        before = demo_counts()
        tty, fake_input = interactive("d", "q")
        with tty, fake_input:
            call_command("clean_ourlives_demo")
        after = demo_counts()
        self.assertEqual(after["orgs"], before["orgs"] - 1)
        # Quit before projects/reps: all Demo projects and test- reps remain.
        self.assertEqual(after["projects"], before["projects"])
        self.assertEqual(after["reps"], before["reps"])

    def test_a_deletes_everything_remaining(self):
        seed_demo()
        before = demo_counts()
        kept = Organization.objects.filter(
            name__startswith="Demo ").order_by("name").first()
        tty, fake_input = interactive("k", "a")
        with tty, fake_input:
            call_command("clean_ourlives_demo")
        after = demo_counts()
        self.assertEqual(after["orgs"], 1)
        self.assertEqual(after["projects"], 0)
        # Reps still referenced by the kept org's orders are PROTECT-kept;
        # reps of deleted orgs are gone.
        self.assertLess(after["reps"], before["reps"])
        self.assertTrue(Rep.objects.filter(
            email__startswith="test-",
            orders__organization=kept).exists())

    def test_non_tty_without_flags_raises(self):
        from django.core.management.base import CommandError
        seed_demo()
        with mock.patch.object(sys.stdin, "isatty", return_value=False):
            with self.assertRaises(CommandError):
                call_command("clean_ourlives_demo")

    def test_pool_total_untouched_but_freed(self):
        from ourlives.models import AppSettings
        seed_demo()
        total_before = AppSettings.get_solo().total_tokens
        call_command("clean_ourlives_demo", yes=True)
        settings = AppSettings.get_solo()
        self.assertEqual(settings.total_tokens, total_before)
        self.assertEqual(settings.tokens_assigned, 0)
