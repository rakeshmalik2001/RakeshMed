from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0012_user_approval_specialty"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="approval_available_for_assignment",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="user",
            name="approval_unavailable_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
