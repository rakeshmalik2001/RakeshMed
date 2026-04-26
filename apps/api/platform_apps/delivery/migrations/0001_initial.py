from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_delivery_zones(apps, schema_editor):
    DeliveryZone = apps.get_model("delivery", "DeliveryZone")
    defaults = [
        {"code": "BLR", "name": "Bangalore Metro", "pincode_prefix": "560", "city": "Bangalore", "state": "Karnataka", "eta_min_hours": 8, "eta_max_hours": 24, "cod_available": True, "is_active": True},
        {"code": "DEL", "name": "Delhi NCR", "pincode_prefix": "110", "city": "Delhi", "state": "Delhi", "eta_min_hours": 12, "eta_max_hours": 24, "cod_available": True, "is_active": True},
        {"code": "MUM", "name": "Mumbai Metro", "pincode_prefix": "400", "city": "Mumbai", "state": "Maharashtra", "eta_min_hours": 12, "eta_max_hours": 24, "cod_available": True, "is_active": True},
        {"code": "HYD", "name": "Hyderabad Metro", "pincode_prefix": "500", "city": "Hyderabad", "state": "Telangana", "eta_min_hours": 12, "eta_max_hours": 24, "cod_available": True, "is_active": True},
        {"code": "NAT", "name": "National Coverage", "pincode_prefix": "1", "city": "India", "state": "", "eta_min_hours": 48, "eta_max_hours": 96, "cod_available": False, "is_active": True},
    ]
    for row in defaults:
        DeliveryZone.objects.get_or_create(code=row["code"], defaults=row)


def unseed_delivery_zones(apps, schema_editor):
    DeliveryZone = apps.get_model("delivery", "DeliveryZone")
    DeliveryZone.objects.filter(code__in=["BLR", "DEL", "MUM", "HYD", "NAT"]).delete()


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("orders", "0009_order_fulfillment_status_and_tracking_reference"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeliveryZone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("code", models.CharField(max_length=24, unique=True)),
                ("pincode_prefix", models.CharField(db_index=True, max_length=6)),
                ("city", models.CharField(blank=True, max_length=120)),
                ("state", models.CharField(blank=True, max_length=120)),
                ("eta_min_hours", models.PositiveIntegerField(default=24)),
                ("eta_max_hours", models.PositiveIntegerField(default=48)),
                ("cod_available", models.BooleanField(default=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["pincode_prefix", "name"]},
        ),
        migrations.CreateModel(
            name="DeliveryShipment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("carrier_name", models.CharField(default="TrueCare Dispatch", max_length=120)),
                ("service_level", models.CharField(choices=[("standard", "Standard"), ("express", "Express")], default="standard", max_length=20)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("assigned", "Assigned"), ("picked_up", "Picked Up"), ("in_transit", "In Transit"), ("out_for_delivery", "Out for Delivery"), ("delivered", "Delivered"), ("failed", "Failed"), ("returned", "Returned"), ("cancelled", "Cancelled")], default="queued", max_length=24)),
                ("tracking_reference", models.CharField(blank=True, max_length=120)),
                ("status_notes", models.CharField(blank=True, max_length=255)),
                ("eta_start", models.DateTimeField(blank=True, null=True)),
                ("eta_end", models.DateTimeField(blank=True, null=True)),
                ("assigned_at", models.DateTimeField(blank=True, null=True)),
                ("dispatched_at", models.DateTimeField(blank=True, null=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("order", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="delivery_shipment", to="orders.order")),
                ("zone", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="shipments", to="delivery.deliveryzone")),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="DeliveryEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("queued", "Queued"), ("assigned", "Assigned"), ("picked_up", "Picked Up"), ("in_transit", "In Transit"), ("out_for_delivery", "Out for Delivery"), ("delivered", "Delivered"), ("failed", "Failed"), ("returned", "Returned"), ("cancelled", "Cancelled")], max_length=24)),
                ("summary", models.CharField(max_length=255)),
                ("meta", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="delivery_events", to=settings.AUTH_USER_MODEL)),
                ("shipment", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="delivery.deliveryshipment")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="deliveryshipment",
            index=models.Index(fields=["status", "updated_at"], name="delivery_shi_status_75935f_idx"),
        ),
        migrations.AddIndex(
            model_name="deliveryshipment",
            index=models.Index(fields=["tracking_reference"], name="delivery_shi_trackin_f31d8d_idx"),
        ),
        migrations.RunPython(seed_delivery_zones, unseed_delivery_zones),
    ]
