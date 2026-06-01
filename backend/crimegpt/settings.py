"""
Django settings for the CrimeGPT project (Week 1).

Configuration is read from environment variables (see .env.example) so that all
team machines run identically under Docker Compose.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load a local .env when present (compose also injects these vars directly).
load_dotenv(BASE_DIR.parent / ".env")


def env_bool(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).lower() in ("1", "true", "yes", "on")


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# --- Security / debug -------------------------------------------------------
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = env_bool("DJANGO_DEBUG", "1")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0")

# --- Applications -----------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "corsheaders",
    "simple_history",
    # Local
    "core",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Captures the request user for django-simple-history audit trails.
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "crimegpt.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "crimegpt.wsgi.application"

# --- Database (PostgreSQL + pgvector) ---------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "crimegpt"),
        "USER": os.environ.get("POSTGRES_USER", "crimegpt"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "crimegpt"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# --- Password validation ----------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internationalization ---------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# --- Static / media ---------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom user model with the IO / SHO / Legal Advisor role field.
AUTH_USER_MODEL = "core.User"

# --- Django REST Framework --------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

# --- CORS (Vite dev server) -------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)
