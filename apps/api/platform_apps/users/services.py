from __future__ import annotations

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.authtoken.models import Token

from platform_apps.audit.services import record_audit_event
from platform_apps.notifications.services import create_notification


ADMIN_APPROVER_ROLES = ("admin", "super_admin")


def build_user_password_reset_url(user, *, request=None) -> str:
    reset_path = reverse(
        "password_reset_confirm",
        kwargs={
            "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
        },
    )
    if request is not None:
        return request.build_absolute_uri(reset_path)
    base_url = (getattr(settings, "BACKEND_BASE_URL", "") or "").strip() or "http://localhost:8000"
    return f"{base_url.rstrip('/')}{reset_path}"


def send_user_password_reset_link(user, *, request=None, initiated_by=None) -> str:
    if not (user.email or "").strip():
        raise ValueError("A verified email address is required to send a password reset link.")

    Token.objects.filter(user=user).delete()
    update_fields = []
    if not user.force_password_reset:
        user.force_password_reset = True
        update_fields.append("force_password_reset")
    if initiated_by is not None and getattr(user, "updated_by_id", None) != getattr(initiated_by, "pk", None):
        user.updated_by = initiated_by
        update_fields.append("updated_by")
    if update_fields:
        user.save(update_fields=[*update_fields, "updated_at"])

    reset_url = build_user_password_reset_url(user, request=request)
    initiated_label = "an administrator" if initiated_by else "the system"
    message = (
        f"Hello {user.full_name or user.email or user.phone_number},\n\n"
        f"A password reset was requested for your RakeshMed account by {initiated_label}.\n"
        f"Use the secure link below to set a new password:\n\n"
        f"{reset_url}\n\n"
        "If you did not expect this request, please contact support immediately."
    )
    send_mail(
        subject="Reset your RakeshMed password",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
    return reset_url


def _admin_email_recipients() -> list[str]:
    from .models import User

    return list(
        User.objects.filter(
            is_active=True,
            approval_status="approved",
            role__in=ADMIN_APPROVER_ROLES,
            email__isnull=False,
        )
        .exclude(email="")
        .values_list("email", flat=True)
    )


def _admin_recipients():
    from .models import User

    return User.objects.filter(
        is_active=True,
        approval_status="approved",
        role__in=ADMIN_APPROVER_ROLES,
    )


def notify_admins_of_pending_approval(user) -> None:
    if user.approval_status != "pending":
        return

    title = f"{user.get_role_display()} approval required"
    body = f"{user.full_name or user.email or user.phone_number} is waiting for approval."
    meta = {
        "alert_key": f"user-approval-request:{user.pk}",
        "user_id": user.pk,
        "role": user.role,
        "approval_status": user.approval_status,
    }
    for admin_user in _admin_recipients():
        create_notification(
            user=admin_user,
            kind="account",
            title=title,
            body=body,
            link="/admin/users/user/",
            meta=meta,
        )

    recipients = _admin_email_recipients()
    if recipients:
        send_mail(
            subject=f"Approval required for {user.get_role_display()} account",
            message=render_to_string("registration/emails/approval_request.txt", {"user_obj": user}),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
        )

    record_audit_event(
        actor=user,
        event_type="approval_request_created",
        entity_type="user",
        entity_id=user.pk,
        message=f"Approval request created for {user.email or user.phone_number}.",
        meta={"role": user.role, "approval_status": user.approval_status},
    )


def notify_user_of_approval_decision(user, *, previous_status: str, actor=None) -> None:
    if user.approval_status == previous_status:
        return
    if user.approval_status not in {"approved", "rejected"}:
        return

    title = (
        "Your RakeshMed account has been approved"
        if user.approval_status == "approved"
        else "Your RakeshMed account request was rejected"
    )
    body = (
        "You can now sign in to your dashboard."
        if user.approval_status == "approved"
        else "Please contact support or an administrator for the next steps."
    )
    if user.approval_notes:
        body = f"{body} Reviewer note: {user.approval_notes}"

    create_notification(
        user=user,
        kind="account",
        title=title,
        body=body,
        link="/login/" if user.approval_status == "approved" else "",
        meta={"approval_status": user.approval_status, "previous_status": previous_status},
    )

    if user.email:
        send_mail(
            subject=title,
            message=render_to_string("registration/emails/approval_decision.txt", {"user_obj": user}),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

    record_audit_event(
        actor=actor,
        actor_label=str(actor) if actor else "System",
        event_type="approval_status_changed",
        entity_type="user",
        entity_id=user.pk,
        message=f"Approval status changed from {previous_status} to {user.approval_status} for {user.email or user.phone_number}.",
        meta={
            "previous_status": previous_status,
            "approval_status": user.approval_status,
            "role": user.role,
            "approval_notes": user.approval_notes,
        },
    )


def _overdue_escalation_recipients(user):
    from .models import User

    recipients: list[User] = []
    if (
        user.approval_assigned_to
        and user.approval_assigned_to.is_active
        and user.approval_assigned_to.approval_status == "approved"
        and (user.approval_assigned_to.is_superuser or user.approval_assigned_to.role in ADMIN_APPROVER_ROLES)
    ):
        recipients.append(user.approval_assigned_to)

    super_admins = list(
        User.objects.filter(
            is_active=True,
            approval_status="approved",
            role="super_admin",
        )
        .exclude(pk__in=[recipient.pk for recipient in recipients])
        .order_by("id")
    )
    recipients.extend(super_admins)

    if recipients:
        return recipients

    return list(_admin_recipients())


def notify_overdue_approval_escalation(user, *, actor=None) -> bool:
    if not user.approval_is_overdue:
        return False

    repeat_window = timezone.timedelta(hours=getattr(settings, "APPROVAL_ESCALATION_REPEAT_HOURS", 6))
    if user.approval_last_escalated_at and timezone.now() - user.approval_last_escalated_at < repeat_window:
        return False

    recipients = _overdue_escalation_recipients(user)
    if not recipients:
        return False

    title = f"Overdue {user.get_role_display().lower()} approval"
    body = (
        f"{user.full_name or user.email or user.phone_number} has exceeded the approval SLA. "
        f"Assigned reviewer: {user.approval_assigned_to or 'Unassigned'}."
    )
    link = f"/admin/approval-queue/{user.pk}/"
    meta = {
        "alert_key": f"user-approval-overdue:{user.pk}",
        "user_id": user.pk,
        "role": user.role,
        "approval_status": user.approval_status,
        "approval_due_at": user.approval_due_at.isoformat() if user.approval_due_at else None,
        "assigned_reviewer_id": user.approval_assigned_to_id,
    }
    for recipient in recipients:
        create_notification(
            user=recipient,
            kind="system_alert",
            title=title,
            body=body,
            link=link,
            meta=meta,
        )

    email_recipients = [recipient.email for recipient in recipients if recipient.email]
    if email_recipients:
        send_mail(
            subject=f"Overdue approval escalation for {user.get_role_display()} account",
            message=render_to_string("registration/emails/approval_overdue.txt", {"user_obj": user}),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=email_recipients,
        )

    user.approval_last_escalated_at = timezone.now()
    user.save(update_fields=["approval_last_escalated_at", "updated_at"])

    record_audit_event(
        actor=actor,
        actor_label=str(actor) if actor else "System",
        event_type="approval_sla_escalated",
        entity_type="user",
        entity_id=user.pk,
        message=f"Approval SLA escalated for {user.email or user.phone_number}.",
        meta={
            "role": user.role,
            "approval_due_at": user.approval_due_at.isoformat() if user.approval_due_at else None,
            "assigned_reviewer_id": user.approval_assigned_to_id,
        },
    )
    return True


def run_overdue_approval_escalations(*, actor=None) -> int:
    from .models import User

    escalated_count = 0
    overdue_candidates = User.objects.filter(
        approval_status="pending",
        role__in=["vendor", "pharmacist"],
        approval_due_at__isnull=False,
        approval_due_at__lt=timezone.now(),
    ).select_related("approval_assigned_to")

    for user in overdue_candidates.iterator():
        if notify_overdue_approval_escalation(user, actor=actor):
            escalated_count += 1

    return escalated_count
