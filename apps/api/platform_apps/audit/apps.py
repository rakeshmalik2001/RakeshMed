from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "platform_apps.audit"
    verbose_name = "Audit and Files"

    def ready(self) -> None:
        from . import signals  # noqa: F401

