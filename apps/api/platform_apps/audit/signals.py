from pathlib import Path

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from platform_apps.catalog.models import Category, Product
from platform_apps.notifications.models import Notification
from platform_apps.orders.models import Order, PaymentAttempt
from platform_apps.prescriptions.models import Prescription
from platform_apps.users.models import User

from .models import AuditLog, ManagedFile


def _write_audit_log(instance, *, event_type: str, entity_type: str, message: str, severity: str = "info", meta=None) -> None:
    AuditLog.objects.create(
        actor=getattr(instance, "uploaded_by", None) or getattr(instance, "user", None),
        actor_label=str(getattr(instance, "uploaded_by", None) or getattr(instance, "user", None) or "System"),
        event_type=event_type,
        entity_type=entity_type,
        entity_id=str(instance.pk or ""),
        severity=severity,
        message=message,
        meta=meta or {},
    )


@receiver(pre_save, sender=ManagedFile)
def track_file_size(sender, instance: ManagedFile, **_kwargs):
    if instance.file and hasattr(instance.file, "size"):
        instance.file_size_bytes = instance.file.size


@receiver(post_save, sender=ManagedFile)
def managed_file_saved(sender, instance: ManagedFile, created: bool, **_kwargs):
    _write_audit_log(
        instance,
        event_type="file_uploaded" if created else "file_updated",
        entity_type="managed_file",
        message=f"{'Uploaded' if created else 'Updated'} file {instance.title}",
        meta={"filename": instance.filename, "category": instance.category},
    )


@receiver(post_delete, sender=ManagedFile)
def managed_file_deleted(sender, instance: ManagedFile, **_kwargs):
    AuditLog.objects.create(
        actor=instance.uploaded_by,
        actor_label=str(instance.uploaded_by or "System"),
        event_type="file_deleted",
        entity_type="managed_file",
        entity_id=str(instance.pk or ""),
        severity="warning",
        message=f"Removed file {instance.title}",
        meta={"filename": Path(instance.file.name).name if instance.file else ""},
    )


def _register_model_audit(model, entity_type: str, label_getter):
    @receiver(post_save, sender=model)
    def _saved(sender, instance, created: bool, **_kwargs):
        _write_audit_log(
            instance,
            event_type=f"{entity_type}_{'created' if created else 'updated'}",
            entity_type=entity_type,
            message=f"{'Created' if created else 'Updated'} {label_getter(instance)}",
        )

    @receiver(post_delete, sender=model)
    def _deleted(sender, instance, **_kwargs):
        AuditLog.objects.create(
            actor=getattr(instance, "user", None),
            actor_label=str(getattr(instance, "user", None) or "System"),
            event_type=f"{entity_type}_deleted",
            entity_type=entity_type,
            entity_id=str(instance.pk or ""),
            severity="warning",
            message=f"Deleted {label_getter(instance)}",
        )


_register_model_audit(User, "user", lambda instance: getattr(instance, "full_name", "") or instance.phone_number)
_register_model_audit(Category, "category", lambda instance: instance.name)
_register_model_audit(Product, "product", lambda instance: instance.name)
_register_model_audit(Order, "order", lambda instance: instance.order_number)
_register_model_audit(Prescription, "prescription", lambda instance: instance.reference_code)
_register_model_audit(PaymentAttempt, "payment", lambda instance: instance.payment_reference)
_register_model_audit(Notification, "notification", lambda instance: instance.title)

