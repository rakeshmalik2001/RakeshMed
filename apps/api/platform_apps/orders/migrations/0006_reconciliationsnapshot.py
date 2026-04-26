from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0005_paymentwebhookevent"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReconciliationSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(default="simulated_gateway", max_length=40)),
                ("captured_total", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("refunded_total", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("pending_refund_count", models.PositiveIntegerField(default=0)),
                ("duplicate_webhooks", models.PositiveIntegerField(default=0)),
                ("processed_webhooks", models.PositiveIntegerField(default=0)),
                ("unmatched_paid_orders", models.PositiveIntegerField(default=0)),
                ("created_by_label", models.CharField(blank=True, max_length=120)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
