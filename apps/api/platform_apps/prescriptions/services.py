from __future__ import annotations

from django.db import transaction

from platform_apps.notifications.services import enqueue_notification, enqueue_role_notification
from platform_apps.notifications.tasks import send_prescription_review_sla_alert_task


def _schedule_on_commit(callback) -> None:
    transaction.on_commit(callback)


def queue_prescription_submitted_notifications(*, prescription) -> None:
    def _enqueue() -> None:
        enqueue_notification(
            user_id=prescription.user_id,
            kind="prescription_update",
            title="Prescription received",
            body=(
                f"We received prescription {prescription.reference_code} for {prescription.patient_name}. "
                f"Our pharmacist team will review it within about {prescription.review_eta_hours} hours."
            ),
            link=f"/account/prescriptions/{prescription.reference_code}",
            meta={"reference_code": prescription.reference_code, "status": prescription.status},
        )
        enqueue_role_notification(
            roles=["admin", "pharmacist", "support_agent"],
            kind="prescription_update",
            title="New prescription awaiting review",
            body=(
                f"{prescription.reference_code} for {prescription.patient_name} "
                f"entered the review queue with {prescription.review_priority} priority."
            ),
            link=f"/admin/prescriptions/{prescription.pk}",
            meta={
                "alert_key": f"prescription:new:{prescription.reference_code}",
                "prescription_id": prescription.pk,
                "reference_code": prescription.reference_code,
                "review_priority": prescription.review_priority,
            },
        )

        countdown_seconds = max(int(prescription.review_eta_hours) * 3600, 0)
        if countdown_seconds > 0:
            try:
                send_prescription_review_sla_alert_task.apply_async(
                    kwargs={"prescription_id": prescription.pk},
                    countdown=countdown_seconds,
                )
            except Exception:
                send_prescription_review_sla_alert_task(prescription_id=prescription.pk)

    _schedule_on_commit(_enqueue)


def queue_prescription_review_notifications(*, prescription) -> None:
    def _enqueue() -> None:
        if prescription.status == "approved":
            title = "Prescription approved"
            body = (
                f"{prescription.reference_code} has been approved for {prescription.patient_name}. "
                "You can continue with checkout."
            )
        elif prescription.status == "rejected":
            title = "Prescription rejected"
            body = (
                f"{prescription.reference_code} was rejected for {prescription.patient_name}. "
                "Please upload a clearer or updated prescription."
            )
        elif prescription.status == "clarification_required":
            title = "Prescription needs clarification"
            detail = prescription.clarification_message or "Our pharmacist team needs more detail before approval."
            body = f"{prescription.reference_code} needs clarification. {detail}"
        else:
            title = "Prescription update"
            body = f"{prescription.reference_code} is now {prescription.status.replace('_', ' ')}."

        enqueue_notification(
            user_id=prescription.user_id,
            kind="prescription_update",
            title=title,
            body=body,
            link=f"/account/prescriptions/{prescription.reference_code}",
            meta={"reference_code": prescription.reference_code, "status": prescription.status},
        )

    _schedule_on_commit(_enqueue)
