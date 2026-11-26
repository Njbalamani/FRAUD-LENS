import importlib.util
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def env(name, default=""):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    value = env(name, str(default)).strip().lower()
    return value in {"1", "true", "yes", "on"}


def env_int(name, default):
    try:
        return int(env(name, str(default)))
    except (TypeError, ValueError):
        return default


def env_float(name, default):
    try:
        return float(env(name, str(default)))
    except (TypeError, ValueError):
        return default


SECRET_KEY = env("FRAUDLENS_SECRET_KEY", "django-insecure-fraudlens-development-key")
DEBUG = env_bool("FRAUDLENS_DEBUG", True)
ALLOWED_HOSTS = [host.strip() for host in env("FRAUDLENS_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "apps.accounts.apps.AccountsConfig",
    "apps.core.apps.CoreConfig",
    "apps.transactions.apps.TransactionsConfig",
    "apps.detection.apps.DetectionConfig",
    "apps.behavior.apps.BehaviorConfig",
    "apps.graph.apps.GraphConfig",
    "apps.investigations.apps.InvestigationsConfig",
    "apps.reports.apps.ReportsConfig",
    "apps.dashboard.apps.DashboardConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.core.middleware.AuditContextMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if importlib.util.find_spec("whitenoise"):
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "fraudlens.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.fraudlens_context",
            ],
        },
    },
]

WSGI_APPLICATION = "fraudlens.wsgi.application"
ASGI_APPLICATION = "fraudlens.asgi.application"

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": (
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": env_int("FRAUDLENS_PAGE_SIZE", 50),
    "DEFAULT_THROTTLE_CLASSES": ("apps.core.throttling.FraudLensRateThrottle",),
    "DEFAULT_THROTTLE_RATES": {"fraudlens": env("FRAUDLENS_API_THROTTLE_RATE", "300/min")},
}

DATABASE_ENGINE = env("FRAUDLENS_DB_ENGINE", "django.db.backends.sqlite3")
if DATABASE_ENGINE == "django.db.backends.postgresql":
    DATABASES = {
        "default": {
            "ENGINE": DATABASE_ENGINE,
            "NAME": env("FRAUDLENS_DB_NAME", "fraudlens"),
            "USER": env("FRAUDLENS_DB_USER", "fraudlens"),
            "PASSWORD": env("FRAUDLENS_DB_PASSWORD", ""),
            "HOST": env("FRAUDLENS_DB_HOST", "localhost"),
            "PORT": env("FRAUDLENS_DB_PORT", "5432"),
            "CONN_MAX_AGE": env_int("FRAUDLENS_DB_CONN_MAX_AGE", 60),
            "OPTIONS": {"sslmode": env("FRAUDLENS_DB_SSLMODE", "prefer")},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / env("FRAUDLENS_DB_NAME", "db.sqlite3"),
            "OPTIONS": {"timeout": 20},
        }
    }

CELERY_BROKER_URL = env("FRAUDLENS_CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("FRAUDLENS_CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TASK_ALWAYS_EAGER = env_bool("FRAUDLENS_CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_EAGER_PROPAGATES = True

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
if importlib.util.find_spec("whitenoise") and "test" not in sys.argv:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }

FRAUDLENS_MODE = env("FRAUDLENS_MODE", "synthetic")
FRAUDLENS_ENABLE_LIVE_DATA = env_bool("FRAUDLENS_ENABLE_LIVE_DATA", False)
FRAUDLENS_MAX_UPLOAD_MB = env_int("FRAUDLENS_MAX_UPLOAD_MB", 5)
FRAUDLENS_MODEL_DIR = BASE_DIR / "datasets" / "models"
FRAUDLENS_BASELINE_WINDOW_DAYS = env_int("FRAUDLENS_BASELINE_WINDOW_DAYS", 30)
FRAUDLENS_AMOUNT_Z_THRESHOLD = env_float("FRAUDLENS_AMOUNT_Z_THRESHOLD", 3.0)
FRAUDLENS_FREQUENCY_Z_THRESHOLD = env_float("FRAUDLENS_FREQUENCY_Z_THRESHOLD", 2.5)
FRAUDLENS_HIGH_RISK_THRESHOLD = env_int("FRAUDLENS_HIGH_RISK_THRESHOLD", 75)
FRAUDLENS_ENABLE_XGBOOST = env_bool("FRAUDLENS_ENABLE_XGBOOST", True)
FRAUDLENS_ENABLE_SHAP = env_bool("FRAUDLENS_ENABLE_SHAP", True)
FRAUDLENS_MODEL_DIR.mkdir(parents=True, exist_ok=True)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"standard": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "standard"}},
    "root": {"handlers": ["console"], "level": env("FRAUDLENS_LOG_LEVEL", "INFO")},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
