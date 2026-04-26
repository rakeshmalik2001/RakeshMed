from __future__ import annotations

from celery import shared_task

from .services import run_overdue_approval_escalations


@shared_task(
    name="users.run_overdue_approval_escalations",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def run_overdue_approval_escalations_task() -> int:
    return run_overdue_approval_escalations()
