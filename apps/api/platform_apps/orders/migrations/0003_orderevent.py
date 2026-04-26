from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("orders", "0002_paymentattempt"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrderEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("placed", "Placed"),
                            ("payment_session_started", "Payment Session Started"),
                            ("payment_captured", "Payment Captured"),
                            ("payment_failed", "Payment Failed"),
                            ("cancelled", "Cancelled"),
                            ("status_updated", "Status Updated"),
                            ("payment_status_updated", "Payment Status Updated"),
                            ("note_updated", "Note Updated"),
                        ],
                        max_length=40,
                    ),
                ),
                ("actor_label", models.CharField(blank=True, max_length=120)),
                ("summary", models.CharField(max_length=255)),
                ("meta", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="order_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="timeline",
                        to="orders.order",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
