from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from platform_apps.catalog.models import Product

from .models import InventoryItem, LowStockRule
from .services import ensure_product_inventory, refresh_product_stock_status


@receiver(post_save, sender=Product)
def ensure_inventory_for_product(sender, instance: Product, created: bool, **_kwargs):
    if created:
        ensure_product_inventory(instance)
        refresh_product_stock_status(instance)


@receiver(post_save, sender=InventoryItem)
def inventory_item_saved(sender, instance: InventoryItem, **_kwargs):
    refresh_product_stock_status(instance.product)


@receiver(post_delete, sender=InventoryItem)
def inventory_item_deleted(sender, instance: InventoryItem, **_kwargs):
    refresh_product_stock_status(instance.product)


@receiver(post_save, sender=LowStockRule)
@receiver(post_delete, sender=LowStockRule)
def low_stock_rule_changed(sender, instance: LowStockRule, **_kwargs):
    refresh_product_stock_status(instance.product)

