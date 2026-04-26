from __future__ import annotations

from platform_apps.users.models import User

from .models import AuditLog


def record_audit_event(
    *,
    actor: User | None = None,
    actor_label: str = "",
    event_type: str,
    entity_type: str,
    entity_id: str | int = "",
    message: str,
    severity: str = "info",
    meta: dict | None = None,
) -> AuditLog:
    resolved_actor_label = actor_label or (
        actor.full_name or actor.phone_number if actor else "System"
    )
    return AuditLog.objects.create(
        actor=actor,
        actor_label=resolved_actor_label,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=str(entity_id or ""),
        severity=severity,
        message=message,
        meta=meta or {},
    )
