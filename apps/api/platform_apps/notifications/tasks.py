from __future__ import annotations

from celery import shared_task
from django.contrib.auth import get_user_model

from .models import Notification
from .services import create_notification


@shared_task(
    name="notifications.create_notification",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def create_notification_task(*, user_id: int, kind: str, title: str, body: str, link: str = "", meta: dict | None = None) -> int | None:
    user_model = get_user_model()
    try:
        user = user_model.objects.get(pk=user_id, is_active=True)
    except user_model.DoesNotExist:
        return None

    notification = create_notification(
        user=user,
        kind=kind,
        title=title,
        body=body,
        link=link,
        meta=meta or {},
    )
    return notification.pk


@shared_task(
    name="notifications.create_role_notification",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def create_role_notification_task(
    *,
    roles: list[str],
    kind: str,
    title: str,
    body: str,
    link: str = "",
    meta: dict | None = None,
) -> int:
    user_model = get_user_model()
    payload = meta or {}
    alert_key = payload.get("alert_key")
    created_count = 0

    for user in user_model.objects.filter(is_active=True, role__in=roles).iterator():
        if alert_key and Notification.objects.filter(
            user=user,
            kind=kind,
            is_read=False,
            meta__alert_key=alert_key,
        ).exists():
            continue
        create_notification(
            user=user,
            kind=kind,
            title=title,
            body=body,
            link=link,
            meta=payload,
        )
        created_count += 1

    return created_count


@shared_task(
    name="notifications.send_prescription_review_sla_alert",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def send_prescription_review_sla_alert_task(*, prescription_id: int) -> int:
    from platform_apps.prescriptions.models import Prescription

    try:
        prescription = Prescription.objects.select_related("user").get(pk=prescription_id)
    except Prescription.DoesNotExist:
        return 0

    if prescription.status not in {"submitted", "pending_review"}:
        return 0

    return create_role_notification_task(
        roles=["admin", "pharmacist", "support_agent"],
        kind="prescription_update",
        title="Prescription review SLA approaching",
        body=(
            f"{prescription.reference_code} for {prescription.patient_name} "
            f"is still awaiting review."
        ),
        link=f"/admin/prescriptions/{prescription.pk}",
        meta={
            "alert_key": f"prescription-sla:{prescription.reference_code}",
            "prescription_id": prescription.pk,
            "reference_code": prescription.reference_code,
            "review_priority": prescription.review_priority,
        },
    )
