from django.db import migrations, models


def seed_inventory_status(apps, schema_editor):
    Order = apps.get_model("orders", "Order")

    for order in Order.objects.all().iterator():
        if order.payment_status == "refunded":
            next_status = "returned"
        elif order.status == "cancelled" or order.payment_status == "failed":
            next_status = "released"
        elif order.status == "confirmed" or order.payment_status == "paid":
            next_status = "completed"
        elif order.status in {"placed", "pending_prescription_review"}:
            next_status = "reserved"
        else:
            next_status = "unreserved"
        Order.objects.filter(pk=order.pk).update(inventory_status=next_status)


def reset_inventory_status(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    Order.objects.update(inventory_status="unreserved")


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0007_settlementbatch_settlemententry"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="inventory_status",
            field=models.CharField(
                choices=[
                    ("unreserved", "Unreserved"),
                    ("reserved", "Reserved"),
                    ("completed", "Completed"),
                    ("released", "Released"),
                    ("returned", "Returned"),
                ],
                default="unreserved",
                max_length=20,
            ),
        ),
        migrations.RunPython(seed_inventory_status, reset_inventory_status),
    ]
