from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("prescriptions", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="prescription",
            name="storage_key",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="prescription",
            name="uploaded_file_size_bytes",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
