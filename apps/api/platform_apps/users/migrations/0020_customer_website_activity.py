from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0019_expand_enterprise_role_choices"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="customer_active_seconds_total",
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="user",
            name="customer_activity_active_tab_id",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="user",
            name="customer_activity_active_tab_seen_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="CustomerWebsiteActivityDaily",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("activity_date", models.DateField(db_index=True)),
                ("active_seconds", models.PositiveIntegerField(default=0)),
                ("heartbeat_count", models.PositiveIntegerField(default=0)),
                ("last_heartbeat_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="website_activity_days", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "ordering": ["-activity_date"],
            },
        ),
        migrations.AddIndex(
            model_name="customerwebsiteactivitydaily",
            index=models.Index(fields=["activity_date", "active_seconds"], name="users_custo_activit_12992d_idx"),
        ),
        migrations.AddIndex(
            model_name="customerwebsiteactivitydaily",
            index=models.Index(fields=["user", "activity_date"], name="users_custo_user_id_bd0507_idx"),
        ),
        migrations.AddConstraint(
            model_name="customerwebsiteactivitydaily",
            constraint=models.UniqueConstraint(fields=("user", "activity_date"), name="unique_customer_website_activity_day"),
        ),
    ]
