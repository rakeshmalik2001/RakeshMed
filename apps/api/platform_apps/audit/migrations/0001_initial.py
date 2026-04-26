from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actor_label", models.CharField(blank=True, max_length=160)),
                ("event_type", models.CharField(max_length=64)),
                ("entity_type", models.CharField(max_length=64)),
                ("entity_id", models.CharField(blank=True, max_length=64)),
                ("severity", models.CharField(choices=[("info", "Info"), ("warning", "Warning"), ("critical", "Critical")], default="info", max_length=16)),
                ("message", models.CharField(max_length=255)),
                ("meta", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_logs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ManagedFile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160)),
                ("category", models.CharField(choices=[("report", "Report"), ("prescription", "Prescription"), ("invoice", "Invoice"), ("compliance", "Compliance"), ("export", "Export"), ("other", "Other")], default="other", max_length=24)),
                ("file", models.FileField(upload_to="backoffice/%Y/%m/%d")),
                ("description", models.TextField(blank=True)),
                ("visibility", models.CharField(choices=[("admin", "Admin"), ("ops", "Ops"), ("all_staff", "All Staff")], default="all_staff", max_length=24)),
                ("file_size_bytes", models.PositiveBigIntegerField(default=0)),
                ("download_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("uploaded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="managed_files", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["event_type", "created_at"], name="audit_event_created_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["entity_type", "entity_id"], name="audit_entity_idx"),
        ),
    ]
