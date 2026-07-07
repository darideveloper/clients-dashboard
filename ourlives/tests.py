from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from ourlives.models import AppSettings, InvitationCode, Project


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


class InvitationCodeBaseTestCase(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name="Test Project")
        AppSettings.get_solo()
        AppSettings.objects.update(total_tokens=100)


class InvitationCodeCreationTests(InvitationCodeBaseTestCase):
    def test_create_invitation_code_with_auto_generated_code(self):
        code = InvitationCode.objects.create(project=self.project, max_use=10)
        self.assertIsNotNone(code.code)
        self.assertNotEqual(code.code, "")
        self.assertTrue(code.is_active)
        self.assertEqual(code.current_use, 0)
        self.assertEqual(code.max_use, 10)
        self.assertEqual(str(code), code.code)

    def test_create_code_within_pool_limit(self):
        code = InvitationCode.objects.create(project=self.project, max_use=10)
        self.assertIsNotNone(code.pk)

    def test_create_code_exceeding_pool_limit(self):
        InvitationCode.objects.create(project=self.project, max_use=100)
        with self.assertRaises(ValidationError):
            InvitationCode.objects.create(project=self.project, max_use=1)


class InvitationCodeUpdateTests(InvitationCodeBaseTestCase):
    def setUp(self):
        super().setUp()
        self.code = InvitationCode.objects.create(
            project=self.project, max_use=10, current_use=3,
        )

    def test_update_increasing_max_use_within_limit(self):
        self.code.max_use = 15
        self.code.save()
        self.code.refresh_from_db()
        self.assertEqual(self.code.max_use, 15)

    def test_update_increasing_max_use_beyond_limit(self):
        other = Project.objects.create(name="Other")
        InvitationCode.objects.create(project=other, max_use=90)
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
        InvitationCode.objects.create(project=other, max_use=97)
        self.code.max_use = 10
        self.code.is_active = True
        with self.assertRaises(ValidationError):
            self.code.save()


class AppSettingsTests(TestCase):
    def setUp(self):
        AppSettings.get_solo()
        AppSettings.objects.update(total_tokens=100)

    def test_computed_properties(self):
        project = Project.objects.create(name="Test")
        InvitationCode.objects.create(project=project, max_use=5, current_use=3)
        InvitationCode.objects.create(project=project, max_use=5, current_use=3)
        InvitationCode.objects.create(project=project, max_use=10, current_use=0)

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

    def test_reduce_total_tokens_below_assigned_succeeds(self):
        project = Project.objects.create(name="Test")
        InvitationCode.objects.create(project=project, max_use=80)
        self.assertEqual(AppSettings.get_solo().tokens_assigned, 80)
        AppSettings.objects.update(total_tokens=50)
        settings = AppSettings.get_solo()
        self.assertEqual(settings.total_tokens, 50)
        with self.assertRaises(ValidationError):
            InvitationCode.objects.create(project=project, max_use=1)
