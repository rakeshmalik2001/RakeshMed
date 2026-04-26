from pathlib import Path
import secrets
from urllib.parse import urljoin

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


def _safe_extension(original_name: str) -> str:
    suffix = Path(original_name).suffix.lower()
    return suffix[:10]


def save_prescription_file(*, file_bytes: bytes, content_type: str, original_name: str) -> dict:
    extension = _safe_extension(original_name)
    generated_name = f"{secrets.token_hex(16)}{extension}"
    storage_key = f"{settings.PRESCRIPTION_UPLOAD_DIR.rstrip('/')}/{generated_name}"
    saved_path = default_storage.save(storage_key, ContentFile(file_bytes))
    file_url = ""
    file_url = resolve_prescription_file_access_url(storage_key=saved_path)
    return {
        "storage_key": saved_path,
        "public_url_or_signed_url": file_url,
        "size_bytes": len(file_bytes),
        "content_type": content_type,
        "original_name": original_name,
        "storage_backend": settings.PRESCRIPTION_STORAGE_BACKEND,
    }


def open_prescription_file(storage_key: str):
    return default_storage.open(storage_key, "rb")


def resolve_prescription_file_access_url(*, storage_key: str, fallback_url: str = "") -> str:
    if settings.PRESCRIPTION_STORAGE_CDN_DOMAIN:
        return urljoin(settings.PRESCRIPTION_STORAGE_CDN_DOMAIN.rstrip("/") + "/", storage_key.lstrip("/"))
    if settings.PRESCRIPTION_STORAGE_PUBLIC_BASE_URL:
        return urljoin(settings.PRESCRIPTION_STORAGE_PUBLIC_BASE_URL.rstrip("/") + "/", storage_key.lstrip("/"))
    try:
        return default_storage.url(storage_key)
    except Exception:
        return fallback_url
