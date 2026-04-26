from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def populate_pending_approval_due_dates(apps, schema_editor):
    user_model = apps.get_model("users", "User")
    sla_hours = 24
    for user in user_model.objects.filter(approval_status="pending", role__in=["vendor", "pharmacist"], approval_due_at__isnull=True):
        created_at = user.created_at or timezone.now()
        user.approval_due_at = created_at + timezone.timedelta(hours=sla_hours)
        user.save(update_fields=["approval_due_at", "updated_at"])


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0009_user_document_verification_statuses"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="approval_assigned_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="approval_assigned_to",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.SET_NULL, related_name="assigned_user_approvals", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="user",
            name="approval_due_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(populate_pending_approval_due_dates, migrations.RunPython.noop),
    ]
