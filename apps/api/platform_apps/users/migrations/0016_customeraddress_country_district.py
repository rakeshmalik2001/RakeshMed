from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0015_user_approval_leave_dates"),
    ]

    operations = [
        migrations.AddField(
            model_name="customeraddress",
            name="country",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="customeraddress",
            name="district",
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
