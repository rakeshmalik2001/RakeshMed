from pathlib import Path
from celery.schedules import crontab
import os
from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parents[2]
SETTINGS_MODULE = os.getenv("DJANGO_SETTINGS_MODULE", "")
LOCAL_LIKE_SETTINGS = SETTINGS_MODULE.endswith(".local") or SETTINGS_MODULE.endswith(".test_sqlite")


def env(name: str, default: str | None = None) -> str | None:
    return os.getenv(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def env_required(name: str, *, fallback: str | None = None, allow_insecure_default: bool = False) -> str:
    value = os.getenv(name)
    if value not in (None, ""):
        return value
    if allow_insecure_default and fallback is not None:
        return fallback
    raise ImproperlyConfigured(f"Missing required environment variable: {name}")


ALLOW_INSECURE_DEFAULTS = env_bool("DJANGO_ALLOW_INSECURE_DEFAULTS", default=LOCAL_LIKE_SETTINGS)
SECRET_KEY = env_required("DJANGO_SECRET_KEY", fallback="change-me", allow_insecure_default=ALLOW_INSECURE_DEFAULTS)
DEBUG = env_bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "platform_apps.health",
    "platform_apps.audit",
    "platform_apps.users",
    "platform_apps.catalog",
    "platform_apps.inventory",
    "platform_apps.delivery",
    "platform_apps.prescriptions",
    "platform_apps.cart",
    "platform_apps.orders",
    "platform_apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "config.middleware.StructuredRequestLoggingMiddleware",
    "config.middleware.ApiVersionHeadersMiddleware",
    "config.middleware.SecurityHeadersMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "platform_apps.users.middleware.AccountStatusMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware"
]

ROOT_URLCONF = "config.urls"

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
                "platform_apps.users.context_processors.portal_navigation",
            ]
        }
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env_required("POSTGRES_DB", fallback="rakeshmed", allow_insecure_default=ALLOW_INSECURE_DEFAULTS),
        "USER": env_required("POSTGRES_USER", fallback="rakeshmed", allow_insecure_default=ALLOW_INSECURE_DEFAULTS),
        "PASSWORD": env_required("POSTGRES_PASSWORD", fallback="rakeshmed", allow_insecure_default=ALLOW_INSECURE_DEFAULTS),
        "HOST": env("POSTGRES_HOST", "localhost"),
        "PORT": env("POSTGRES_PORT", "5433"),
        "CONN_MAX_AGE": int(env("POSTGRES_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": env_bool("POSTGRES_CONN_HEALTH_CHECKS", default=True),
        "OPTIONS": {
            **(
                {"sslmode": env("POSTGRES_SSLMODE", "prefer")}
                if env("POSTGRES_SSLMODE")
                else {}
            ),
        },
    }
}

if env("POSTGRES_REPLICA_HOST"):
    DATABASES["replica"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_REPLICA_DB", env_required("POSTGRES_DB", fallback="rakeshmed", allow_insecure_default=ALLOW_INSECURE_DEFAULTS)),
        "USER": env("POSTGRES_REPLICA_USER", env_required("POSTGRES_USER", fallback="rakeshmed", allow_insecure_default=ALLOW_INSECURE_DEFAULTS)),
        "PASSWORD": env("POSTGRES_REPLICA_PASSWORD", env_required("POSTGRES_PASSWORD", fallback="rakeshmed", allow_insecure_default=ALLOW_INSECURE_DEFAULTS)),
        "HOST": env("POSTGRES_REPLICA_HOST", "localhost"),
        "PORT": env("POSTGRES_REPLICA_PORT", env("POSTGRES_PORT", "5433")),
        "CONN_MAX_AGE": int(env("POSTGRES_REPLICA_CONN_MAX_AGE", env("POSTGRES_CONN_MAX_AGE", "60"))),
        "CONN_HEALTH_CHECKS": env_bool(
            "POSTGRES_REPLICA_CONN_HEALTH_CHECKS",
            default=env_bool("POSTGRES_CONN_HEALTH_CHECKS", default=True),
        ),
        "OPTIONS": {
            **(
                {"sslmode": env("POSTGRES_REPLICA_SSLMODE", env("POSTGRES_SSLMODE", "prefer"))}
                if env("POSTGRES_REPLICA_SSLMODE", env("POSTGRES_SSLMODE", "prefer"))
                else {}
            ),
        },
    }

REDIS_URL = env("REDIS_URL", "redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "socket_connect_timeout": float(env("REDIS_SOCKET_CONNECT_TIMEOUT", "1.0")),
            "socket_timeout": float(env("REDIS_SOCKET_TIMEOUT", "1.0")),
            "retry_on_timeout": False,
        },
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "platform_apps.users.authentication.ExpiringTokenAuthentication"
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated"
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "auth_send_otp": env("AUTH_SEND_OTP_RATE", "5/hour"),
        "auth_verify_otp": env("AUTH_VERIFY_OTP_RATE", "10/hour"),
        "public_catalog_read": env("PUBLIC_CATALOG_READ_RATE", "600/minute"),
        "public_catalog_search": env("PUBLIC_CATALOG_SEARCH_RATE", "180/minute"),
        "public_serviceability": env("PUBLIC_SERVICEABILITY_RATE", "240/minute"),
        "checkout": env("CHECKOUT_RATE", "20/minute"),
        "payment_session": env("PAYMENT_SESSION_RATE", "30/minute"),
        "prescription_upload": env("PRESCRIPTION_UPLOAD_RATE", "20/hour"),
        "payment_webhook": env("PAYMENT_WEBHOOK_RATE", "3000/minute"),
    },
}

AUTH_USER_MODEL = "users.User"
AUTHENTICATION_BACKENDS = [
    "platform_apps.users.backends.EmailOrPhoneBackend",
    "django.contrib.auth.backends.ModelBackend",
]
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/login/"
LOGOUT_REDIRECT_URL = "/login/"
ENABLE_DB_REPLICA_ROUTING = env_bool("ENABLE_DB_REPLICA_ROUTING", default=False)
DATABASE_ROUTERS = (
    ["config.db_router.ReadReplicaRouter"] if ENABLE_DB_REPLICA_ROUTING and "replica" in DATABASES else []
)

LANGUAGE_CODE = "en-in"
TIME_ZONE = env("DJANGO_TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = env("DJANGO_MEDIA_URL", "/media/")
MEDIA_ROOT = Path(env("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media")))
PRESCRIPTION_UPLOAD_DIR = env("PRESCRIPTION_UPLOAD_DIR", "prescriptions")
PRESCRIPTION_MAX_FILE_SIZE_BYTES = int(env("PRESCRIPTION_MAX_FILE_SIZE_BYTES", str(10 * 1024 * 1024)))
APPROVAL_DOCUMENT_MAX_FILE_SIZE_BYTES = int(env("APPROVAL_DOCUMENT_MAX_FILE_SIZE_BYTES", str(5 * 1024 * 1024)))
APPROVAL_DOCUMENT_ALLOWED_EXTENSIONS = env_list("APPROVAL_DOCUMENT_ALLOWED_EXTENSIONS", ".pdf,.jpg,.jpeg,.png")
APPROVAL_REVIEW_SLA_HOURS = int(env("APPROVAL_REVIEW_SLA_HOURS", "24"))
APPROVAL_ESCALATION_REPEAT_HOURS = int(env("APPROVAL_ESCALATION_REPEAT_HOURS", "6"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = env_list("DJANGO_CORS_ALLOWED_ORIGINS", "http://localhost:3000")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:3000")
FRONTEND_BASE_URL = env("FRONTEND_BASE_URL", "http://localhost:3000")
FRONTEND_CUSTOMER_ACCOUNT_URL = env("FRONTEND_CUSTOMER_ACCOUNT_URL", f"{FRONTEND_BASE_URL.rstrip('/')}/account")
FRONTEND_CUSTOMER_REGISTER_URL = env("FRONTEND_CUSTOMER_REGISTER_URL", f"{FRONTEND_BASE_URL.rstrip('/')}/signup")
SESSION_COOKIE_SECURE = env_bool("DJANGO_SESSION_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_SECURE = env_bool("DJANGO_CSRF_COOKIE_SECURE", default=not DEBUG)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = env("DJANGO_SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = env("DJANGO_CSRF_COOKIE_SAMESITE", "Lax")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SECURE_BROWSER_XSS_FILTER = True
SECURE_HSTS_SECONDS = int(env("DJANGO_SECURE_HSTS_SECONDS", "0" if DEBUG else "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=not DEBUG)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", default=not DEBUG)
OTP_MAX_ATTEMPTS = int(env("OTP_MAX_ATTEMPTS", "5"))
EXPOSE_DEBUG_OTP_CODE = env_bool("EXPOSE_DEBUG_OTP_CODE", default=LOCAL_LIKE_SETTINGS and DEBUG)
LOGIN_THROTTLE_FAILURE_LIMIT = int(env("LOGIN_THROTTLE_FAILURE_LIMIT", "5"))
LOGIN_THROTTLE_WINDOW_SECONDS = int(env("LOGIN_THROTTLE_WINDOW_SECONDS", "900"))
PORTAL_MFA_TTL_SECONDS = int(env("PORTAL_MFA_TTL_SECONDS", "300"))
PORTAL_MFA_RESEND_COOLDOWN_SECONDS = int(env("PORTAL_MFA_RESEND_COOLDOWN_SECONDS", "30"))
AUTH_TOKEN_TTL_SECONDS = int(env("AUTH_TOKEN_TTL_SECONDS", str(7 * 24 * 60 * 60)))
PUBLIC_API_CACHE_TTL_SECONDS = int(env("PUBLIC_API_CACHE_TTL_SECONDS", "120"))
PUBLIC_SEARCH_CACHE_TTL_SECONDS = int(env("PUBLIC_SEARCH_CACHE_TTL_SECONDS", "45"))
SERVICEABILITY_CACHE_TTL_SECONDS = int(env("SERVICEABILITY_CACHE_TTL_SECONDS", "300"))
IDEMPOTENCY_PENDING_TTL_SECONDS = int(env("IDEMPOTENCY_PENDING_TTL_SECONDS", "30"))
IDEMPOTENCY_COMPLETED_TTL_SECONDS = int(env("IDEMPOTENCY_COMPLETED_TTL_SECONDS", "3600"))
PRESCRIPTION_FILE_URL_TTL_SECONDS = int(env("PRESCRIPTION_FILE_URL_TTL_SECONDS", "900"))
PRESCRIPTION_STORAGE_BACKEND = env("PRESCRIPTION_STORAGE_BACKEND", "local")
PRESCRIPTION_STORAGE_BUCKET = env("PRESCRIPTION_STORAGE_BUCKET", "")
PRESCRIPTION_STORAGE_REGION = env("PRESCRIPTION_STORAGE_REGION", "")
PRESCRIPTION_STORAGE_ENDPOINT = env("PRESCRIPTION_STORAGE_ENDPOINT", "")
PRESCRIPTION_STORAGE_CDN_DOMAIN = env("PRESCRIPTION_STORAGE_CDN_DOMAIN", "")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        }
    },
    "loggers": {
        "rakeshmed.request": {
            "handlers": ["console"],
            "level": env("REQUEST_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
        "rakeshmed.auth": {
            "handlers": ["console"],
            "level": env("AUTH_LOG_LEVEL", "INFO"),
            "propagate": False,
        }
    },
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TASK_ACKS_LATE = env_bool("CELERY_TASK_ACKS_LATE", default=True)
CELERY_TASK_REJECT_ON_WORKER_LOST = env_bool("CELERY_TASK_REJECT_ON_WORKER_LOST", default=True)
CELERY_WORKER_PREFETCH_MULTIPLIER = int(env("CELERY_WORKER_PREFETCH_MULTIPLIER", "1"))
CELERY_WORKER_MAX_TASKS_PER_CHILD = int(env("CELERY_WORKER_MAX_TASKS_PER_CHILD", "1000"))
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "visibility_timeout": int(env("CELERY_VISIBILITY_TIMEOUT_SECONDS", str(60 * 60))),
}
CELERY_TASK_DEFAULT_RETRY_DELAY = int(env("CELERY_TASK_DEFAULT_RETRY_DELAY", "30"))
CELERY_TASK_DEFAULT_MAX_RETRIES = int(env("CELERY_TASK_DEFAULT_MAX_RETRIES", "5"))
CELERY_BEAT_SCHEDULE = {
    "users-run-overdue-approval-escalations": {
        "task": "users.run_overdue_approval_escalations",
        "schedule": crontab(minute=0),
    },
}

PAYMENT_PROVIDER_NAME = env("PAYMENT_PROVIDER_NAME", "simulated_gateway")
PAYMENT_PROVIDER_PUBLIC_KEY = env("PAYMENT_PROVIDER_PUBLIC_KEY", "tc_test_public_key")
PAYMENT_PROVIDER_SECRET_KEY = env_required("PAYMENT_PROVIDER_SECRET_KEY", fallback="tc_test_secret_key", allow_insecure_default=ALLOW_INSECURE_DEFAULTS)
PAYMENT_WEBHOOK_SECRET = env_required("PAYMENT_WEBHOOK_SECRET", fallback="tc_webhook_secret", allow_insecure_default=ALLOW_INSECURE_DEFAULTS)
PAYMENT_WEBHOOK_PREVIOUS_SECRET = env("PAYMENT_WEBHOOK_PREVIOUS_SECRET", "")
PAYMENT_WEBHOOK_MAX_AGE_SECONDS = int(env("PAYMENT_WEBHOOK_MAX_AGE_SECONDS", "900"))
ALLOW_PUBLIC_HEALTH_ENDPOINTS = env_bool("ALLOW_PUBLIC_HEALTH_ENDPOINTS", default=LOCAL_LIKE_SETTINGS)
ALLOW_PUBLIC_METRICS_ENDPOINTS = env_bool("ALLOW_PUBLIC_METRICS_ENDPOINTS", default=LOCAL_LIKE_SETTINGS)
HEALTHCHECK_ACCESS_TOKEN = env("HEALTHCHECK_ACCESS_TOKEN", "")
METRICS_ACCESS_TOKEN = env("METRICS_ACCESS_TOKEN", "")
PRESCRIPTION_STORAGE_PUBLIC_BASE_URL = env("PRESCRIPTION_STORAGE_PUBLIC_BASE_URL", "")
BACKEND_BASE_URL = env("BACKEND_BASE_URL", "http://localhost:8000")

COMPLIANCE_COMPANY_NAME = env("NEXT_PUBLIC_COMPANY_NAME", "TrueCare Health Services Private Limited")
COMPLIANCE_SUPPORT_EMAIL = env("NEXT_PUBLIC_SUPPORT_EMAIL", "support@truecare.in")
COMPLIANCE_GRIEVANCE_EMAIL = env("NEXT_PUBLIC_GRIEVANCE_EMAIL", "grievance@truecare.in")
COMPLIANCE_GRIEVANCE_OFFICER = env("NEXT_PUBLIC_GRIEVANCE_OFFICER", "Kishor Kumar")
COMPLIANCE_DRUG_LICENSE_NUMBER = env(
    "NEXT_PUBLIC_PHARMACY_LICENSE_NUMBER",
    "MH-TRC-RDL-000214 / MH-TRC-WDL-000215",
)
COMPLIANCE_DRUG_LICENSE_AUTHORITY = env(
    "NEXT_PUBLIC_PHARMACY_LICENSE_AUTHORITY",
    "Maharashtra Food and Drug Administration",
)
COMPLIANCE_PHARMACIST_IN_CHARGE = env(
    "NEXT_PUBLIC_PHARMACIST_IN_CHARGE",
    "Registered Pharmacist On Duty",
)
COMPLIANCE_PHARMACIST_REGISTRATION_NUMBER = env(
    "NEXT_PUBLIC_PHARMACIST_REGISTRATION_NUMBER",
    "PCI-REG-TO-BE-CONFIRMED",
)
EMAIL_BACKEND = env("DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DJANGO_DEFAULT_FROM_EMAIL", "noreply@rakeshmed.local")
