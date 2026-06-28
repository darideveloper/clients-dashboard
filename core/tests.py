import os
import re
import tempfile
from unittest import mock

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db.models.deletion import ProtectedError
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from core.models import Brand, Membership
from utils.callbacks import primary_palette_css, site_icon


class BrandModelTests(TestCase):
    def test_default_brand_name(self):
        self.assertEqual(Brand.DEFAULT_NAME, "Default Brand")

    def test_default_brand_default_color(self):
        self.assertEqual(Brand.DEFAULT_PRIMARY_COLOR, "#C92FFF")

    def test_get_or_create_default_is_idempotent(self):
        a = Brand.get_or_create_default()
        b = Brand.get_or_create_default()
        self.assertEqual(a.pk, b.pk)
        self.assertEqual(a.name, Brand.DEFAULT_NAME)

    def test_brand_logo_optional(self):
        brand = Brand.objects.create(name="NoLogo")
        self.assertFalse(bool(brand.logo))
        self.assertFalse(brand.has_logo)

    def test_str_returns_name(self):
        brand = Brand.objects.create(name="Acme")
        self.assertEqual(str(brand), "Acme")


class MembershipTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", email="a@x.test")
        self.brand = Brand.objects.create(name="Acme")

    def test_user_brand_setter_creates_membership(self):
        self.user.brand = self.brand
        self.assertTrue(Membership.objects.filter(user=self.user, brand=self.brand).exists())

    def test_user_brand_getter_returns_brand(self):
        Membership.objects.create(user=self.user, brand=self.brand)
        self.assertEqual(self.user.brand, self.brand)

    def test_user_brand_none_deletes_membership(self):
        Membership.objects.create(user=self.user, brand=self.brand)
        self.user.brand = None
        self.user.refresh_from_db()
        self.assertFalse(Membership.objects.filter(user=self.user).exists())

    def test_user_without_membership_brand_is_none(self):
        self.assertIsNone(self.user.brand)

    def test_membership_brand_protect_blocks_delete(self):
        Membership.objects.create(user=self.user, brand=self.brand)
        with self.assertRaises(ProtectedError):
            self.brand.delete()

    def test_membership_user_cascade(self):
        Membership.objects.create(user=self.user, brand=self.brand)
        self.user.delete()
        self.assertFalse(Membership.objects.filter(brand=self.brand).exists())


class UserAdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@x.test", password="x"
        )
        self.staff = User.objects.create_user(
            username="staff", email="s@x.test", password="x", is_staff=True
        )
        from core.admin import UserAdmin
        self.user_admin = UserAdmin(User, None)

    def test_superuser_sees_membership_inline(self):
        request = self.factory.get("/")
        request.user = self.superuser
        inlines = self.user_admin.get_inlines(request, obj=None)
        self.assertTrue(inlines)
        from core.admin import MembershipInline
        self.assertIn(MembershipInline, inlines)

    def test_staff_does_not_see_membership_inline(self):
        request = self.factory.get("/")
        request.user = self.staff
        inlines = self.user_admin.get_inlines(request, obj=None)
        self.assertEqual(inlines, [])


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class UserAdminAddFormIntegrationTests(TestCase):
    """Integration tests covering the admin add-user form save path."""

    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username="su", email="su@x.test", password="x"
        )
        self.staff = User.objects.create_user(
            username="staff", email="s@x.test", password="x", is_staff=True
        )
        self.client.force_login(self.superuser)
        self.add_url = reverse("admin:auth_user_add")
        Brand.objects.filter(name=Brand.DEFAULT_NAME).delete()

    def _get_csrf(self, content):
        m = re.search(r'csrfmiddlewaretoken.*?value="([^"]+)"', content)
        return m.group(1) if m else ""

    def _post(self, **overrides):
        r = self.client.get(self.add_url)
        post = {
            "csrfmiddlewaretoken": self._get_csrf(r.content.decode()),
            "username": overrides.pop("username", "newuser"),
            "email": overrides.pop("email", "n@x.test"),
            "first_name": "",
            "last_name": "",
            "is_staff": "1",
            "is_active": "1",
            "password1": "Sup3rS3cret!",
            "password2": "Sup3rS3cret!",
            "_save": "Save",
            "membership-TOTAL_FORMS": "0",
            "membership-INITIAL_FORMS": "0",
            "membership-MIN_NUM_FORMS": "0",
            "membership-MAX_NUM_FORMS": "1000",
        }
        post.update(overrides)
        return self.client.post(self.add_url, post)

    def test_superuser_adds_user_with_no_brand_gets_default_brand(self):
        r = self._post()
        self.assertEqual(r.status_code, 302)
        u = User.objects.get(username="newuser")
        self.assertEqual(u.brand, Brand.get_or_create_default())
        self.assertEqual(Membership.objects.filter(user=u).count(), 1)

    def test_superuser_adds_user_with_explicit_brand_gets_that_brand(self):
        explicit = Brand.objects.create(name="Explicit")
        r = self._post(
            **{
                "membership-TOTAL_FORMS": "1",
                "membership-0-brand": str(explicit.pk),
            }
        )
        self.assertEqual(r.status_code, 302)
        u = User.objects.get(username="newuser")
        self.assertEqual(u.brand, explicit)
        self.assertEqual(Membership.objects.filter(user=u).count(), 1)
        # Default Brand should NOT have been auto-created
        self.assertFalse(Brand.objects.filter(name=Brand.DEFAULT_NAME).exists())

    def test_staff_cannot_access_add_form(self):
        # Staff (non-superuser) lacks the add-user permission; the admin
        # returns 403. This is an intentional guard: only superusers can
        # create users (and therefore assign brand links).
        self.client.force_login(self.staff)
        r = self.client.get(self.add_url)
        self.assertEqual(r.status_code, 403)


class SiteIconCallbackTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="u", email="u@x.test")
        self.brand = Brand.objects.create(name="B")
        # Stub the staticfiles manifest so favicon lookups don't fail in tests.
        self._static_patcher = mock.patch(
            "utils.callbacks.static", return_value="/static/favicon.png"
        )
        self._static_patcher.start()

    def tearDown(self):
        self._static_patcher.stop()

    def test_unauthenticated_returns_favicon(self):
        request = self.factory.get("/")
        request.user = mock.Mock(is_authenticated=False)
        self.assertIn("favicon", site_icon(request))

    def test_authenticated_no_brand_returns_favicon(self):
        request = self.factory.get("/")
        request.user = self.user
        self.assertIn("favicon", site_icon(request))

    def test_authenticated_brand_no_logo_returns_favicon(self):
        Membership.objects.create(user=self.user, brand=self.brand)
        request = self.factory.get("/")
        request.user = self.user
        self.assertIn("favicon", site_icon(request))

    def test_authenticated_brand_with_logo_returns_logo_url(self):
        Membership.objects.create(user=self.user, brand=self.brand)
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.write(b"fake")
        tmp.close()
        self.brand.logo.save("logo.png", SimpleUploadedFile("logo.png", b"fake"), save=True)
        try:
            request = self.factory.get("/")
            request.user = self.user
            url = site_icon(request)
            self.assertNotIn("favicon", url)
        finally:
            if self.brand.logo:
                self.brand.logo.delete(save=False)


class PrimaryPaletteCssTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="u", email="u@x.test")

    def test_unauthenticated_returns_empty(self):
        request = self.factory.get("/")
        request.user = mock.Mock(is_authenticated=False)
        self.assertEqual(primary_palette_css(request), "")

    def test_no_brand_returns_empty(self):
        request = self.factory.get("/")
        request.user = self.user
        self.assertEqual(primary_palette_css(request), "")

    def test_brand_with_color_returns_palette(self):
        brand = Brand.objects.create(name="B", primary_color="#0066FF")
        Membership.objects.create(user=self.user, brand=brand)
        request = self.factory.get("/")
        request.user = self.user
        css = primary_palette_css(request)
        self.assertIn(":root", css)
        self.assertIn("oklch(from #0066FF", css)
        self.assertIn("--color-primary-500", css)

    def test_achromatic_color_uses_grayscale(self):
        brand = Brand.objects.create(name="B", primary_color="#000000")
        Membership.objects.create(user=self.user, brand=brand)
        request = self.factory.get("/")
        request.user = self.user
        css = primary_palette_css(request)
        self.assertIn("oklch(0.68 0 0)", css)
        self.assertNotIn("oklch(from #000000", css)


class SeedBrandsCommandTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="orphan", email="o@x.test")

    def test_creates_default_brand(self):
        self.assertFalse(Brand.objects.filter(name=Brand.DEFAULT_NAME).exists())
        call_command("seed_brands")
        self.assertTrue(Brand.objects.filter(name=Brand.DEFAULT_NAME).exists())

    def test_assigns_orphan_users_to_default_brand(self):
        call_command("seed_brands")
        user = User.objects.get(username="orphan")
        self.assertIsNotNone(user.brand)
        self.assertEqual(user.brand.name, Brand.DEFAULT_NAME)

    def test_idempotent(self):
        call_command("seed_brands")
        first_count = Brand.objects.count()
        call_command("seed_brands")
        second_count = Brand.objects.count()
        self.assertEqual(first_count, 1)
        self.assertEqual(second_count, 1)

    def test_moves_legacy_avatar_files(self):
        media_root = tempfile.mkdtemp()
        with override_settings(MEDIA_ROOT=media_root):
            brand = Brand.objects.create(name="HasFile")
            brand_pk = brand.pk
            legacy_dir = os.path.join(media_root, "avatars", f"user_{brand_pk}")
            os.makedirs(legacy_dir, exist_ok=True)
            legacy_path = os.path.join(legacy_dir, "pic.png")
            with open(legacy_path, "wb") as f:
                f.write(b"data")
            brand.logo.name = f"avatars/user_{brand_pk}/pic.png"
            brand.save()

            call_command("seed_brands")

            brand.refresh_from_db()
            expected_dir = os.path.join(media_root, "brands", f"brand_{brand.pk}")
            self.assertTrue(
                os.path.isdir(expected_dir),
                f"expected dir at {expected_dir}; not found",
            )
            new_path = os.path.join(expected_dir, "pic.png")
            self.assertTrue(
                os.path.exists(new_path),
                f"expected file at {new_path}; not found",
            )
            self.assertFalse(os.path.exists(legacy_path))
            self.assertTrue(brand.logo)
            self.assertIn(f"brand_{brand.pk}", brand.logo.name)

    def test_missing_source_file_skipped_silently(self):
        media_root = tempfile.mkdtemp()
        with override_settings(MEDIA_ROOT=media_root):
            brand = Brand.objects.create(name="B")
            brand.logo.name = "avatars/user_999/ghost.png"
            brand.save()
            call_command("seed_brands")
            brand.refresh_from_db()
            self.assertEqual(brand.logo.name, "avatars/user_999/ghost.png")


class TemplateOverrideTests(TestCase):
    def test_override_template_wins(self):
        from django.template.loader import get_template
        tpl = get_template("unfold/helpers/navigation_user.html")
        origin = tpl.origin.name
        self.assertIn("project/templates", origin)
        self.assertNotIn("site-packages", origin)


class AvatarUploadSizeTests(TestCase):
    def test_oversized_logo_rejected(self):
        from core.validators import validate_image_size
        big = mock.Mock(size=3 * 1024 * 1024)
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            validate_image_size(big)

    def test_under_cap_accepted(self):
        from core.validators import validate_image_size
        small = mock.Mock(size=1024)
        validate_image_size(small)
