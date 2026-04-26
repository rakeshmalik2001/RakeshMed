from django.db import migrations, models


def seed_fulfillment_status(apps, schema_editor):
    Order = apps.get_model("orders", "Order")

    for order in Order.objects.all().iterator():
        if order.inventory_status == "returned" or order.payment_status == "refunded":
            next_status = "returned"
        elif order.status == "cancelled":
            next_status = "cancelled"
        elif order.inventory_status == "completed":
            next_status = "delivered"
        elif order.status == "confirmed" or order.payment_status == "paid":
            next_status = "packed"
        else:
            next_status = "queued"
        Order.objects.filter(pk=order.pk).update(fulfillment_status=next_status)


def reset_fulfillment_status(apps, schema_editor):
    Order = apps.get_model("orders", "Order")
    Order.objects.update(fulfillment_status="queued", tracking_reference="")


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0008_order_inventory_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="fulfillment_status",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"),
                    ("packed", "Packed"),
                    ("shipped", "Shipped"),
                    ("delivered", "Delivered"),
                    ("returned", "Returned"),
                    ("cancelled", "Cancelled"),
                ],
                default="queued",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="tracking_reference",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.RunPython(seed_fulfillment_status, reset_fulfillment_status),
    ]
