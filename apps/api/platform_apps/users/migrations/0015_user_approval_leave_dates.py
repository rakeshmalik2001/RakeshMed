from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0014_user_approval_shift_window"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="approval_leave_dates",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
