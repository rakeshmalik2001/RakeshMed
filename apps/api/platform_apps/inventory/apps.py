from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "platform_apps.inventory"
    verbose_name = "Inventory"

    def ready(self) -> None:
        from . import signals  # noqa: F401

