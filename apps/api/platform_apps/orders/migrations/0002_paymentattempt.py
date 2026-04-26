from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(default="simulated_gateway", max_length=40)),
                ("payment_reference", models.CharField(max_length=64, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("created", "Created"),
                            ("pending", "Pending"),
                            ("authorized", "Authorized"),
                            ("captured", "Captured"),
                            ("failed", "Failed"),
                        ],
                        default="created",
                        max_length=20,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("raw_payload", models.JSONField(blank=True, default=dict)),
                ("initiated_at", models.DateTimeField(auto_now_add=True)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payment_attempts",
                        to="orders.order",
                    ),
                ),
            ],
            options={
                "ordering": ["-initiated_at"],
            },
        ),
    ]
