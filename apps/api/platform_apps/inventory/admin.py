from django.contrib import admin

from .models import InventoryItem, LowStockRule, StockLocation, StockMovement


@admin.register(StockLocation)
class StockLocationAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_display = ("name", "code", "kind", "is_active", "sort_order")
    list_filter = ("kind", "is_active")
    search_fields = ("name", "code")
    ordering = ("sort_order", "name")


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_select_related = ("product", "location")
    list_display = ("product", "location", "quantity_on_hand", "reserved_quantity", "inbound_quantity", "available_quantity_display", "updated_at")
    list_filter = ("location", "product__stock_status")
    search_fields = ("product__name", "product__sku", "location__name", "location__code")
    autocomplete_fields = ("product", "location")
    readonly_fields = ("updated_at", "available_quantity_display")

    @admin.display(description="Available")
    def available_quantity_display(self, obj: InventoryItem) -> int:
        return obj.available_quantity


@admin.register(LowStockRule)
class LowStockRuleAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_select_related = ("product", "location")
    list_display = ("product", "threshold_quantity", "location", "updated_at")
    search_fields = ("product__name", "product__sku", "location__name")
    autocomplete_fields = ("product", "location")
    readonly_fields = ("updated_at",)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_per_page = 30
    list_select_related = ("product", "location", "created_by", "inventory_item")
    list_display = ("created_at", "product", "location", "movement_type", "quantity_delta", "reference", "created_by")
    list_filter = ("movement_type", "location")
    search_fields = ("product__name", "product__sku", "reference", "notes", "created_by__phone_number")
    autocomplete_fields = ("product", "inventory_item", "location", "created_by")
    readonly_fields = ("created_at",)

