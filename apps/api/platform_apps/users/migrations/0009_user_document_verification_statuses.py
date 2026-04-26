# Generated manually for approval document verification statuses.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0008_user_approval_documents"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="pharmacist_registration_document_status",
            field=models.CharField(
                choices=[("not_required", "Not Required"), ("pending", "Pending Review"), ("verified", "Verified"), ("rejected", "Rejected")],
                default="not_required",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="vendor_license_document_status",
            field=models.CharField(
                choices=[("not_required", "Not Required"), ("pending", "Pending Review"), ("verified", "Verified"), ("rejected", "Rejected")],
                default="not_required",
                max_length=16,
            ),
        ),
    ]
