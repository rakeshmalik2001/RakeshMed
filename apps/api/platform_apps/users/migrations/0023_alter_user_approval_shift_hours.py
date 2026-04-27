from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0022_alter_user_approval_shift_weekdays"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="approval_shift_start_hour",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="user",
            name="approval_shift_end_hour",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
