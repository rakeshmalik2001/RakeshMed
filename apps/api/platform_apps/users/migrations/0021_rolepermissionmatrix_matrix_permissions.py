from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0020_customer_website_activity"),
    ]

    operations = [
        migrations.AddField(
            model_name="rolepermissionmatrix",
            name="matrix_permissions",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
