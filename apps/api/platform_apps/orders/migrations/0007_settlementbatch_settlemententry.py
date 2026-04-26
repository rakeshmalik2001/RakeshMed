from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0006_reconciliationsnapshot"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SettlementBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(default="simulated_gateway", max_length=40)),
                ("batch_reference", models.CharField(max_length=64, unique=True)),
                ("period_start", models.DateTimeField()),
                ("period_end", models.DateTimeField()),
                ("total_captured", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("total_refunded", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("total_net", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("closed", "Closed")], default="draft", max_length=16)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="settlement_batches", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SettlementEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("gross_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("refund_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("net_amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("settlement_status", models.CharField(choices=[("settled", "Settled"), ("refunded", "Refunded"), ("netted", "Netted")], default="settled", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="settlement_entries", to="orders.order")),
                ("payment_attempt", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="settlement_entries", to="orders.paymentattempt")),
                ("refund_request", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="settlement_entries", to="orders.refundrequest")),
                ("settlement_batch", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="entries", to="orders.settlementbatch")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
