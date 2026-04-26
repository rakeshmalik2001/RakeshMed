from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0013_user_approval_availability"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="approval_shift_end_hour",
            field=models.PositiveSmallIntegerField(default=18),
        ),
        migrations.AddField(
            model_name="user",
            name="approval_shift_start_hour",
            field=models.PositiveSmallIntegerField(default=9),
        ),
        migrations.AddField(
            model_name="user",
            name="approval_shift_weekdays",
            field=models.CharField(default="0,1,2,3,4", max_length=32),
        ),
    ]
