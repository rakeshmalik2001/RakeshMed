from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0017_user_enterprise_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserSavedFilterView",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("filters", models.JSONField(blank=True, default=dict)),
                ("is_default", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_filter_views", to="users.user")),
            ],
            options={
                "ordering": ["-updated_at"],
                "unique_together": {("owner", "name")},
            },
        ),
        migrations.CreateModel(
            name="RolePermissionMatrix",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("customer", "Customer"), ("vendor", "Vendor"), ("super_admin", "Super Admin"), ("admin", "Admin"), ("catalog_manager", "Catalog Manager"), ("pharmacist", "Pharmacist"), ("warehouse_operator", "Warehouse Operator"), ("support_agent", "Support Agent"), ("finance", "Finance"), ("viewer", "Viewer")], max_length=32, unique=True)),
                ("user_create", models.BooleanField(default=False)),
                ("user_read", models.BooleanField(default=True)),
                ("user_update", models.BooleanField(default=False)),
                ("user_delete", models.BooleanField(default=False)),
                ("user_lock", models.BooleanField(default=False)),
                ("user_unlock", models.BooleanField(default=False)),
                ("user_export", models.BooleanField(default=False)),
                ("user_reset_password", models.BooleanField(default=False)),
                ("user_audit_view", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["role"],
            },
        ),
    ]
