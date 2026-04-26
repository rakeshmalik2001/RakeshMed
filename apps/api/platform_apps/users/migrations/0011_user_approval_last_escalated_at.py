from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0010_user_approval_assignment_sla"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="approval_last_escalated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
