# Generated manually for portal approval workflow.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_user_account_status_alter_user_role"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="approval_status",
            field=models.CharField(
                choices=[("approved", "Approved"), ("pending", "Pending Approval"), ("rejected", "Rejected")],
                default="approved",
                max_length=16,
            ),
        ),
    ]
