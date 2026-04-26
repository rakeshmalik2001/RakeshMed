from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0004_refundrequest_and_statuses"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentWebhookEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(default="simulated_gateway", max_length=40)),
                ("event_id", models.CharField(max_length=120, unique=True)),
                ("event_type", models.CharField(max_length=80)),
                ("payment_reference", models.CharField(blank=True, max_length=64)),
                ("order_number", models.CharField(blank=True, max_length=32)),
                ("signature", models.CharField(blank=True, max_length=255)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("was_duplicate", models.BooleanField(default=False)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
