from django.core.management.base import BaseCommand

from platform_apps.users.services import run_overdue_approval_escalations


class Command(BaseCommand):
    help = "Escalate overdue pending pharmacist and vendor approval requests."

    def handle(self, *args, **options):
        escalated_count = run_overdue_approval_escalations()
        self.stdout.write(self.style.SUCCESS(f"Escalated {escalated_count} overdue approval(s)."))
