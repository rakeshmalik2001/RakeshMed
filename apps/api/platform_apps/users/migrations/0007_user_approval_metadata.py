# Generated manually for approval review metadata.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_user_approval_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="approval_notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="user",
            name="approval_reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="approval_reviewed_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reviewed_user_approvals", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="user",
            name="business_name",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="user",
            name="pharmacist_registration_number",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="user",
            name="vendor_license_number",
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
