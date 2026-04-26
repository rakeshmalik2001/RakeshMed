from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0016_customeraddress_country_district"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="account_status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("inactive", "Inactive"),
                    ("blocked", "Blocked"),
                    ("suspended", "Suspended"),
                    ("deleted", "Deleted"),
                ],
                default="active",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="username",
            field=models.CharField(blank=True, max_length=80, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="user",
            name="employee_code",
            field=models.CharField(blank=True, max_length=80, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="user",
            name="type_of_user",
            field=models.CharField(
                choices=[
                    ("employee", "Employee"),
                    ("partner", "Partner"),
                    ("customer", "Customer"),
                    ("system", "System"),
                ],
                default="employee",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="department",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="user",
            name="designation",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="user",
            name="country",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="user",
            name="state",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="user",
            name="district",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="user",
            name="address",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="user",
            name="email_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="account_locked",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="mfa_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="force_password_reset",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="failed_login_attempts",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="user",
            name="last_login_ip",
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="password_last_changed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="remarks",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="user",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_users",
                to="users.user",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updated_users",
                to="users.user",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="deleted_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="deleted_users",
                to="users.user",
            ),
        ),
    ]
