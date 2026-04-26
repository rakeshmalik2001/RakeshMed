from django.db import migrations, models


ENTERPRISE_ROLE_CHOICES = [
    ("customer", "Customer"),
    ("vendor", "Vendor"),
    ("pharmacist", "Pharmacist"),
    ("admin", "Admin"),
    ("super_admin", "Super Admin"),
    ("warehouse_operator", "Warehouse Operator"),
    ("delivery_agent", "Delivery Agent"),
    ("support_agent", "Support Agent"),
    ("finance", "Finance"),
    ("catalog_manager", "Catalog Manager"),
    ("operations_manager", "Operations Manager"),
    ("procurement_manager", "Procurement Manager"),
    ("compliance_officer", "Compliance Officer"),
    ("security_admin", "Security Admin"),
    ("auditor", "Auditor"),
    ("doctor", "Doctor"),
    ("marketing_manager", "Marketing Manager"),
    ("vendor_staff", "Vendor Staff"),
    ("viewer", "Viewer"),
]


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0018_usersavedfilterview_rolepermissionmatrix"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(choices=ENTERPRISE_ROLE_CHOICES, default="customer", max_length=32),
        ),
        migrations.AlterField(
            model_name="rolepermissionmatrix",
            name="role",
            field=models.CharField(choices=ENTERPRISE_ROLE_CHOICES, max_length=32, unique=True),
        ),
    ]
