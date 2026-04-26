from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delivery", "0002_backfill_existing_shipments"),
    ]

    operations = [
        migrations.AddField(
            model_name="deliveryshipment",
            name="failure_reason",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="deliveryshipment",
            name="reattempt_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="deliveryshipment",
            name="next_attempt_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="deliveryshipment",
            name="failed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
