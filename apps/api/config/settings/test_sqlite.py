from pathlib import Path

from .local import *

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test.sqlite3",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "rakeshmed-test-cache",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
MEDIA_ROOT = BASE_DIR / "test-media"
APPROVAL_DOCUMENT_MAX_FILE_SIZE_BYTES = 1024 * 1024
