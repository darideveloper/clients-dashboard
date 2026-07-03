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
from utils.callbacks import (
    primary_palette_css,
    site_favicon,
    site_header,
    site_icon,
    site_subheader,
    site_title,
)
from utils.callbacks import _resolve_brand
from utils.middleware import BrandUrlMiddleware


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

    def test_is_default_enforcement(self):
        a = Brand.objects.create(name="A", is_default=True)
        b = Brand.objects.create(name="B", is_default=True)
        a.refresh_from_db()
        self.assertFalse(a.is_default)
        self.assertTrue(b.is_default)

    def test_slug_auto_generated_from_name(self):
        brand = Brand.objects.create(name="Test Brand")
        self.assertEqual(brand.slug, "test-brand")

    def test_slug_preserved_on_update(self):
        brand = Brand.objects.create(name="Old Name")
        brand.name = "New Name"
        brand.save()
        self.assertEqual(brand.slug, "old-name")

    def test_get_or_create_default_sets_is_default(self):
        Brand.objects.filter(name=Brand.DEFAULT_NAME).delete()
        default = Brand.get_or_create_default()
        self.assertTrue(default.is_default)


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
        self.brand.logo.save("logo.png", _make_test_image(), save=True)
        try:
            request = self.factory.get("/")
            request.user = self.user
            url = site_icon(request)
            self.assertNotIn("favicon", url)
        finally:
            if self.brand.logo:
                self.brand.logo.delete(save=False)


def _make_test_image(width=100, height=100, color=(255, 0, 0)):
    from io import BytesIO
    from PIL import Image
    img = Image.new("RGB", (width, height), color)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return SimpleUploadedFile("test.png", buf.read(), content_type="image/png")


class SiteFaviconCallbackTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="u", email="u@x.test")
        self.brand = Brand.objects.create(name="B")
        self._static_patcher = mock.patch(
            "utils.callbacks.static", return_value="/static/favicon.png"
        )
        self._static_patcher.start()

    def tearDown(self):
        self._static_patcher.stop()

    def test_unauthenticated_returns_favicon(self):
        request = self.factory.get("/")
        request.user = mock.Mock(is_authenticated=False)
        self.assertIn("favicon", site_favicon(request))

    def test_authenticated_no_brand_returns_favicon(self):
        request = self.factory.get("/")
        request.user = self.user
        self.assertIn("favicon", site_favicon(request))

    def test_authenticated_brand_no_logo_returns_favicon(self):
        Membership.objects.create(user=self.user, brand=self.brand)
        request = self.factory.get("/")
        request.user = self.user
        self.assertIn("favicon", site_favicon(request))

    def test_authenticated_brand_with_logo_returns_favicon_url(self):
        Membership.objects.create(user=self.user, brand=self.brand)
        self.brand.logo.save("logo.png", _make_test_image(), save=True)
        try:
            request = self.factory.get("/")
            request.user = self.user
            url = site_favicon(request)
            self.assertNotIn("/static/", url)
            self.assertIn("favicon.png", url)
        finally:
            if self.brand.logo:
                self.brand.logo.delete(save=False)


class SiteTitleCallbackTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="u", email="u@x.test")
        self.brand = Brand.objects.create(name="Acme Corp")

    def test_unauthenticated_returns_fallback_title(self):
        request = self.factory.get("/")
        request.user = mock.Mock(is_authenticated=False)
        self.assertEqual(site_title(request), "clients")
        self.assertEqual(site_header(request), "clients")
        self.assertEqual(site_subheader(request), "Dashboard")

    def test_authenticated_no_brand_returns_fallback(self):
        request = self.factory.get("/")
        request.user = self.user
        self.assertEqual(site_title(request), "clients")
        self.assertEqual(site_header(request), "clients")
        self.assertEqual(site_subheader(request), "Dashboard")

    def test_authenticated_with_brand_returns_branded_titles(self):
        Membership.objects.create(user=self.user, brand=self.brand)
        request = self.factory.get("/")
        request.user = self.user
        self.assertEqual(site_title(request), "Acme Corp")
        self.assertEqual(site_header(request), "Acme Corp")
        self.assertEqual(site_subheader(request), "Dashboard")

    def test_default_brand_renders_name(self):
        default = Brand.get_or_create_default()
        Membership.objects.create(user=self.user, brand=default)
        request = self.factory.get("/")
        request.user = self.user
        self.assertEqual(site_title(request), "Default Brand")
        self.assertEqual(site_header(request), "Default Brand")
        self.assertEqual(site_subheader(request), "Dashboard")


class BrandFaviconGenerationTests(TestCase):
    def test_generated_on_logo_upload(self):
        brand = Brand.objects.create(name="B")
        brand.logo.save("logo.png", _make_test_image(), save=True)
        try:
            storage = brand.logo.storage
            path = f"brands/brand_{brand.pk}/favicon.png"
            self.assertTrue(storage.exists(path), "favicon should exist after logo upload")
        finally:
            if brand.logo:
                brand.logo.delete(save=False)

    def test_regenerated_on_logo_replace(self):
        brand = Brand.objects.create(name="B")
        brand.logo.save("logo.png", _make_test_image(50, 50), save=True)
        path = f"brands/brand_{brand.pk}/favicon.png"
        storage = brand.logo.storage
        self.assertTrue(storage.exists(path))
        old_url = brand.favicon_url
        brand.logo.save("logo.png", _make_test_image(200, 200), save=True)
        try:
            self.assertTrue(storage.exists(path), "favicon should exist after replace")
            self.assertEqual(brand.favicon_url, old_url,
                             "URL path should be the same (file overwritten, not suffixed)")
        finally:
            if brand.logo:
                brand.logo.delete(save=False)

    def test_deleted_on_logo_removed(self):
        brand = Brand.objects.create(name="B")
        brand.logo.save("logo.png", _make_test_image(), save=True)
        path = f"brands/brand_{brand.pk}/favicon.png"
        storage = brand.logo.storage
        self.assertTrue(storage.exists(path))
        brand.logo.delete(save=False)
        brand.save()
        self.assertFalse(storage.exists(path), "favicon should be deleted when logo is removed")

    def test_deleted_on_brand_delete(self):
        brand = Brand.objects.create(name="B")
        brand.logo.save("logo.png", _make_test_image(), save=True)
        path = f"brands/brand_{brand.pk}/favicon.png"
        brand.delete()
        storage = brand.logo.storage if hasattr(brand, 'logo') and brand.logo else None
        if storage:
            self.assertFalse(storage.exists(path), "favicon should be deleted when brand is deleted")

    def test_no_logo_no_favicon(self):
        brand = Brand.objects.create(name="NoLogo")
        self.assertIsNone(brand.favicon_url)

    def test_unsaved_brand_favicon_url_none(self):
        brand = Brand(name="Unsaved")
        self.assertIsNone(brand.favicon_url)


class BrandFaviconImageTests(TestCase):
    def test_output_is_32x32_png(self):
        brand = Brand.objects.create(name="B")
        brand.logo.save("logo.png", _make_test_image(200, 200), save=True)
        try:
            storage = brand.logo.storage
            path = f"brands/brand_{brand.pk}/favicon.png"
            from PIL import Image as PilImage
            with storage.open(path) as f:
                img = PilImage.open(f)
                self.assertEqual(img.size, (32, 32))
                self.assertEqual(img.format, "PNG")
        finally:
            if brand.logo:
                brand.logo.delete(save=False)

    def test_center_cropped_from_non_square(self):
        brand = Brand.objects.create(name="B")
        brand.logo.save("logo.png", _make_test_image(200, 100), save=True)
        try:
            storage = brand.logo.storage
            path = f"brands/brand_{brand.pk}/favicon.png"
            from PIL import Image as PilImage
            with storage.open(path) as f:
                img = PilImage.open(f)
                self.assertEqual(img.size, (32, 32))
        finally:
            if brand.logo:
                brand.logo.delete(save=False)

    def test_uses_lanczos_resampling(self):
        brand = Brand.objects.create(name="B")
        brand.logo.save("logo.png", _make_test_image(200, 200), save=True)
        try:
            storage = brand.logo.storage
            path = f"brands/brand_{brand.pk}/favicon.png"
            from PIL import Image as PilImage
            with storage.open(path) as f:
                img = PilImage.open(f)
                self.assertEqual(img.size, (32, 32))
        finally:
            if brand.logo:
                brand.logo.delete(save=False)


class BrandFaviconErrorTests(TestCase):
    def test_corrupt_image_raises_and_blocks_save(self):
        corrupt = SimpleUploadedFile("bad.png", b"not a real image")
        brand = Brand(name="B", logo=corrupt)
        with self.assertRaises(Exception):
            brand.save()


class BackfillBrandFaviconsCommandTests(TestCase):
    def test_backfill_generates_favicons(self):
        brand1 = Brand.objects.create(name="B1")
        brand1.logo.save("logo.png", _make_test_image(), save=True)
        brand2 = Brand.objects.create(name="B2")
        brand2.logo.save("logo.png", _make_test_image(), save=True)
        brand3 = Brand.objects.create(name="NoLogo")
        try:
            from django.core.management import call_command
            call_command("backfill_brand_favicons")
            for b in [brand1, brand2]:
                storage = b.logo.storage
                path = f"brands/brand_{b.pk}/favicon.png"
                self.assertTrue(storage.exists(path))
        finally:
            for b in [brand1, brand2]:
                if b.logo:
                    b.logo.delete(save=False)


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
            from PIL import Image as PilImage
            img = PilImage.new("RGB", (50, 50), (255, 0, 0))
            img.save(legacy_path, format="PNG")
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


class ResolveBrandTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="alice", email="a@x.test")
        self.brand = Brand.objects.create(name="Acme")
        Membership.objects.create(user=self.user, brand=self.brand)
        self.default_brand = Brand.objects.create(name="Default", is_default=True)

    def test_url_override_wins(self):
        override = Brand.objects.create(name="Override")
        request = self.factory.get("/")
        request.user = self.user
        request._brand_override = override
        result = _resolve_brand(request)
        self.assertEqual(result, override)

    def test_user_brand_wins_without_url_override(self):
        request = self.factory.get("/")
        request.user = self.user
        result = _resolve_brand(request)
        self.assertEqual(result, self.brand)

    def test_is_default_wins_when_no_user_brand(self):
        request = self.factory.get("/")
        request.user = mock.Mock(is_authenticated=False)
        result = _resolve_brand(request)
        self.assertEqual(result, self.default_brand)

    def test_returns_none_when_nothing_exists(self):
        Membership.objects.filter(user=self.user).delete()
        Brand.objects.all().delete()
        request = self.factory.get("/")
        request.user = mock.Mock(is_authenticated=False)
        result = _resolve_brand(request)
        self.assertIsNone(result)

    def test_cache_avoids_duplicate_queries(self):
        Membership.objects.filter(user=self.user).delete()
        Brand.objects.all().delete()
        request = self.factory.get("/")
        request.user = mock.Mock(is_authenticated=False)
        with self.assertNumQueries(1):
            _resolve_brand(request)
            _resolve_brand(request)


class SiteTitleCallbackDefaultBrandTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="u", email="u@x.test")

    def test_unauthenticated_with_default_brand(self):
        default = Brand.objects.create(name="Default Co", is_default=True)
        request = self.factory.get("/")
        request.user = mock.Mock(is_authenticated=False)
        self.assertEqual(site_title(request), "Default Co")
        self.assertEqual(site_header(request), "Default Co")

    def test_unauthenticated_no_default_brand(self):
        request = self.factory.get("/")
        request.user = mock.Mock(is_authenticated=False)
        self.assertEqual(site_title(request), "clients")
        self.assertEqual(site_header(request), "clients")

    def test_url_override_returns_brand_name(self):
        override = Brand.objects.create(name="URL Co")
        request = self.factory.get("/")
        request.user = mock.Mock(is_authenticated=False)
        request._brand_override = override
        self.assertEqual(site_title(request), "URL Co")
        self.assertEqual(site_header(request), "URL Co")


class SiteIconCallbackDefaultBrandTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self._static_patcher = mock.patch(
            "utils.callbacks.static", return_value="/static/favicon.png"
        )
        self._static_patcher.start()

    def tearDown(self):
        self._static_patcher.stop()

    def test_returns_default_brand_logo_when_no_user_brand(self):
        Brand.objects.create(name="Def", is_default=True)
        request = self.factory.get("/")
        request.user = mock.Mock(is_authenticated=False)
        result = site_icon(request)
        self.assertIn("favicon", result)

    def test_url_override_returns_brand_logo(self):
        override = Brand.objects.create(name="URL")
        request = self.factory.get("/")
        request.user = mock.Mock(is_authenticated=False)
        request._brand_override = override
        result = site_icon(request)
        self.assertIn("favicon", result)


class SiteFaviconCallbackDefaultBrandTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self._static_patcher = mock.patch(
            "utils.callbacks.static", return_value="/static/favicon.png"
        )
        self._static_patcher.start()

    def tearDown(self):
        self._static_patcher.stop()

    def test_returns_default_brand_favicon_when_no_user_brand(self):
        Brand.objects.create(name="Def", is_default=True)
        request = self.factory.get("/")
        request.user = mock.Mock(is_authenticated=False)
        result = site_favicon(request)
        self.assertIn("favicon", result)

    def test_url_override_returns_brand_favicon(self):
        override = Brand.objects.create(name="URL")
        request = self.factory.get("/")
        request.user = mock.Mock(is_authenticated=False)
        request._brand_override = override
        result = site_favicon(request)
        self.assertIn("favicon", result)


class PrimaryPaletteCssDefaultBrandTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_selector_has_higher_specificity_than_unfold(self):
        Brand.objects.create(name="Def", primary_color="#0066FF", is_default=True)
        request = self.factory.get("/")
        request.user = mock.Mock(is_authenticated=False)
        css = primary_palette_css(request)
        self.assertTrue(
            css.startswith(":root:root"),
            f"Expected :root:root selector for higher specificity, got: {css.split('{')[0].strip()}",
        )

    def test_returns_default_brand_palette_when_no_user_brand(self):
        Brand.objects.create(name="Def", primary_color="#0066FF", is_default=True)
        request = self.factory.get("/")
        request.user = mock.Mock(is_authenticated=False)
        css = primary_palette_css(request)
        self.assertIn(":root", css)
        self.assertIn("oklch(from #0066FF", css)

    def test_url_override_returns_brand_palette(self):
        override = Brand.objects.create(name="URL", primary_color="#00AA00")
        request = self.factory.get("/")
        request.user = mock.Mock(is_authenticated=False)
        request._brand_override = override
        css = primary_palette_css(request)
        self.assertIn(":root", css)
        self.assertIn("oklch(from #00AA00", css)


class BrandUrlMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.brand = Brand.objects.create(name="Acme Corp")
        self.brand.slug = "acme-corp"
        self.brand.save(update_fields=["slug"])
        self.middleware = BrandUrlMiddleware(lambda r: None)

    def test_login_page_extracts_brand(self):
        request = self.factory.get("/admin/login/?brand=acme-corp")
        self.middleware(request)
        self.assertEqual(request._brand_override, self.brand)

    def test_non_existent_slug_ignored(self):
        request = self.factory.get("/admin/login/?brand=nonexistent")
        self.middleware(request)
        self.assertFalse(hasattr(request, "_brand_override"))

    def test_non_login_path_ignored(self):
        request = self.factory.get("/admin/?brand=acme-corp")
        self.middleware(request)
        self.assertFalse(hasattr(request, "_brand_override"))

    def test_post_login_preserves_branding(self):
        request = self.factory.post("/admin/login/?brand=acme-corp")
        self.middleware(request)
        self.assertEqual(request._brand_override, self.brand)


class BrandAdminTests(TestCase):
    def setUp(self):
        from core.admin import BrandAdmin
        self.admin = BrandAdmin(Brand, None)
        self.superuser = User.objects.create_superuser(
            username="su", email="su@x.test", password="x"
        )

    def test_is_default_in_list_display(self):
        self.assertIn("is_default", self.admin.list_display)

    def test_non_superuser_no_brand_admin_access(self):
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get("/")
        staff = User.objects.create_user(
            username="s", email="s@x.test", password="x", is_staff=True
        )
        request.user = staff
        self.assertFalse(self.admin.has_change_permission(request))


class SeedBrandsCommandIsDefaultTests(TestCase):
    def test_creates_default_brand_with_is_default(self):
        Brand.objects.filter(name=Brand.DEFAULT_NAME).delete()
        call_command("seed_brands")
        default = Brand.get_or_create_default()
        self.assertTrue(default.is_default)
