from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0011_user_approval_last_escalated_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="approval_specialty",
            field=models.CharField(
                choices=[
                    ("all", "All Approval Types"),
                    ("vendor", "Vendor Reviews"),
                    ("pharmacist", "Pharmacist Reviews"),
                ],
                default="all",
                max_length=16,
            ),
        ),
    ]
