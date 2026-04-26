from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_default_inventory(apps, schema_editor):
    Product = apps.get_model("catalog", "Product")
    InventoryItem = apps.get_model("inventory", "InventoryItem")
    LowStockRule = apps.get_model("inventory", "LowStockRule")
    StockLocation = apps.get_model("inventory", "StockLocation")

    main_location, _created = StockLocation.objects.get_or_create(
        code="MAIN",
        defaults={
            "name": "Main Warehouse",
            "kind": "warehouse",
            "is_active": True,
            "sort_order": 0,
        },
    )

    for product in Product.objects.all():
        if product.stock_status == "in_stock":
            quantity = 24
        elif product.stock_status == "low_stock":
            quantity = 4
        else:
            quantity = 0

        InventoryItem.objects.get_or_create(
            product=product,
            location=main_location,
            defaults={
                "quantity_on_hand": quantity,
                "reserved_quantity": 0,
                "inbound_quantity": 0,
            },
        )
        LowStockRule.objects.get_or_create(product=product, defaults={"threshold_quantity": 5})


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="StockLocation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("code", models.CharField(max_length=24, unique=True)),
                ("kind", models.CharField(choices=[("warehouse", "Warehouse"), ("pharmacy", "Pharmacy"), ("returns", "Returns"), ("quarantine", "Quarantine")], default="warehouse", max_length=24)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["sort_order", "name"]},
        ),
        migrations.CreateModel(
            name="InventoryItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quantity_on_hand", models.IntegerField(default=0)),
                ("reserved_quantity", models.PositiveIntegerField(default=0)),
                ("inbound_quantity", models.PositiveIntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("location", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inventory_items", to="inventory.stocklocation")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inventory_items", to="catalog.product")),
            ],
            options={"ordering": ["product__name", "location__sort_order", "location__name"], "unique_together": {("product", "location")}},
        ),
        migrations.CreateModel(
            name="LowStockRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("threshold_quantity", models.PositiveIntegerField(default=5)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("location", models.ForeignKey(blank=True, help_text="Optional location-specific threshold. Leave empty to evaluate across all active locations.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="low_stock_rules", to="inventory.stocklocation")),
                ("product", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="low_stock_rule", to="catalog.product")),
            ],
            options={"ordering": ["product__name"]},
        ),
        migrations.CreateModel(
            name="StockMovement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("movement_type", models.CharField(choices=[("restock", "Restock"), ("adjustment", "Adjustment"), ("sale_allocation", "Sale Allocation"), ("sale_release", "Sale Release"), ("sale_complete", "Sale Complete"), ("return", "Return"), ("damage", "Damage"), ("transfer_in", "Transfer In"), ("transfer_out", "Transfer Out"), ("manual_count", "Manual Count")], default="adjustment", max_length=24)),
                ("quantity_delta", models.IntegerField()),
                ("reference", models.CharField(blank=True, max_length=120)),
                ("notes", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="inventory_movements", to=settings.AUTH_USER_MODEL)),
                ("inventory_item", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="movements", to="inventory.inventoryitem")),
                ("location", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="movements", to="inventory.stocklocation")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stock_movements", to="catalog.product")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="inventoryitem",
            index=models.Index(fields=["product", "location"], name="inventory_i_product_5f36d8_idx"),
        ),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(fields=["product", "created_at"], name="inventory_s_product_5fc641_idx"),
        ),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(fields=["location", "created_at"], name="inventory_s_locatio_2d5cc5_idx"),
        ),
        migrations.RunPython(seed_default_inventory, migrations.RunPython.noop),
    ]
