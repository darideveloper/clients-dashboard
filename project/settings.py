import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from django.templatetags.static import static

from utils.callbacks import site_favicon, site_header, site_icon, site_subheader, site_title

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env first to get ENV value
load_dotenv(BASE_DIR / ".env")
ENV = os.getenv("ENV", "dev")

# Load environment-specific file
load_dotenv(BASE_DIR / f".env.{ENV}")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h.strip()]

HOST = os.getenv("HOST", "").rstrip("/")

# Storage location constants are always defined (no AttributeError if storage_backends is imported in dev)
_AWS_PROJECT_FOLDER = os.getenv("AWS_PROJECT_FOLDER", "")
STATIC_LOCATION = f"{_AWS_PROJECT_FOLDER}/static" if _AWS_PROJECT_FOLDER else "static"
PUBLIC_MEDIA_LOCATION = f"{_AWS_PROJECT_FOLDER}/media" if _AWS_PROJECT_FOLDER else "media"
PRIVATE_MEDIA_LOCATION = f"{_AWS_PROJECT_FOLDER}/private" if _AWS_PROJECT_FOLDER else "private"


# Application definition

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "solo",
    "storages",
    "core",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "utils.middleware.BrandUrlMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "project" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "utils.context_processors.user_palette",
            ],
            "libraries": {
                "sidebar_extras": "utils.templatetags.sidebar_extras",
            },
        },
    },
]

WSGI_APPLICATION = "project.wsgi.application"


# Database
IS_TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

if IS_TESTING:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "testing.sqlite3",
        }
    }
else:
    _options = {}
    if os.environ.get("DB_ENGINE") == "django.db.backends.mysql":
        _options = {
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            "charset": "utf8mb4",
        }

    DATABASES = {
        "default": {
            "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.sqlite3"),
            "NAME": os.environ.get("DB_NAME", BASE_DIR / "db.sqlite3"),
            "USER": os.environ.get("DB_USER", ""),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", ""),
            "OPTIONS": _options,
        }
    }


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True


# Static & media files
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS
_cors_allowed = os.getenv("CORS_ALLOWED_ORIGINS")
if _cors_allowed and _cors_allowed != "None":
    CORS_ALLOWED_ORIGINS = [
        origin.strip().rstrip("/") for origin in _cors_allowed.split(",") if origin.strip()
    ]

# CSRF
_csrf_trusted = os.getenv("CSRF_TRUSTED_ORIGINS")
if _csrf_trusted and _csrf_trusted != "None":
    CSRF_TRUSTED_ORIGINS = [
        origin.strip().rstrip("/") for origin in _csrf_trusted.split(",") if origin.strip()
    ]

# Date/time formats
DATE_FORMAT = "d/b/Y"
TIME_FORMAT = "H:i"
DATETIME_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"

# Storage
STORAGE_AWS = os.getenv("STORAGE_AWS") == "True"

if STORAGE_AWS:
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME")
    AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL")
    AWS_S3_CUSTOM_DOMAIN = os.getenv("AWS_S3_CUSTOM_DOMAIN") or None
    AWS_PROJECT_FOLDER = _AWS_PROJECT_FOLDER
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
    AWS_DEFAULT_ACL = None

    STORAGES = {
        "default": {"BACKEND": "project.storage_backends.PublicMediaStorage"},
        "staticfiles": {"BACKEND": "project.storage_backends.StaticStorage"},
        "private": {"BACKEND": "project.storage_backends.PrivateMediaStorage"},
    }
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }


# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "project.pagination.CustomPageNumberPagination",
    "PAGE_SIZE": 12,
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "EXCEPTION_HANDLER": "project.handlers.custom_exception_handler",
}


# django-unfold
UNFOLD = {
    "SITE_TITLE": lambda request: site_title(request),
    "SITE_HEADER": lambda request: site_header(request),
    "SITE_SUBHEADER": lambda request: site_subheader(request),
    "SITE_URL": "/",
    "SITE_ICON": lambda request: site_icon(request),
    "SITE_SYMBOL": "directions_car",
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/png",
            "href": lambda request: site_favicon(request),
        },
    ],
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "ENVIRONMENT": "utils.callbacks.environment_callback",
    "THEME": "light",
    "COLORS": {
        "primary": {
            "50": "oklch(0.97 0.02 296)",
            "100": "oklch(0.92 0.04 296)",
            "200": "oklch(0.85 0.08 296)",
            "300": "oklch(0.75 0.15 296)",
            "400": "oklch(0.70 0.22 296)",
            "500": "oklch(0.68 0.28 296)",
            "600": "oklch(0.60 0.25 296)",
            "700": "oklch(0.50 0.20 296)",
            "800": "oklch(0.40 0.16 296)",
            "900": "oklch(0.30 0.12 296)",
            "950": "oklch(0.20 0.08 296)",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [],

    },
}
