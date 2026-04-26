from __future__ import annotations

import logging

from .models import Notification

logger = logging.getLogger(__name__)


def create_notification(*, user, kind: str, title: str, body: str, link: str = "", meta: dict | None = None) -> Notification:
    return Notification.objects.create(
        user=user,
        kind=kind,
        title=title,
        body=body,
        link=link,
        meta=meta or {},
    )


def enqueue_notification(
    *,
    user_id: int,
    kind: str,
    title: str,
    body: str,
    link: str = "",
    meta: dict | None = None,
):
    from .tasks import create_notification_task

    try:
        return create_notification_task.delay(
            user_id=user_id,
            kind=kind,
            title=title,
            body=body,
            link=link,
            meta=meta or {},
        )
    except Exception:
        logger.exception("Falling back to synchronous notification creation for user_id=%s", user_id)
        return create_notification_task(
            user_id=user_id,
            kind=kind,
            title=title,
            body=body,
            link=link,
            meta=meta or {},
        )


def enqueue_role_notification(
    *,
    roles: list[str] | tuple[str, ...],
    kind: str,
    title: str,
    body: str,
    link: str = "",
    meta: dict | None = None,
):
    from .tasks import create_role_notification_task

    normalized_roles = list(dict.fromkeys(roles))
    try:
        return create_role_notification_task.delay(
            roles=normalized_roles,
            kind=kind,
            title=title,
            body=body,
            link=link,
            meta=meta or {},
        )
    except Exception:
        logger.exception("Falling back to synchronous role notifications for roles=%s", normalized_roles)
        return create_role_notification_task(
            roles=normalized_roles,
            kind=kind,
            title=title,
            body=body,
            link=link,
            meta=meta or {},
        )
