# Generated manually for approval document uploads.

from django.db import migrations, models

import platform_apps.users.models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_user_approval_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="pharmacist_registration_document",
            field=models.FileField(blank=True, upload_to=platform_apps.users.models.approval_document_upload_to),
        ),
        migrations.AddField(
            model_name="user",
            name="vendor_license_document",
            field=models.FileField(blank=True, upload_to=platform_apps.users.models.approval_document_upload_to),
        ),
    ]
