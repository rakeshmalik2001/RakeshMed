from django.contrib import admin

from .models import DeliveryEvent, DeliveryShipment, DeliveryZone


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "pincode_prefix", "city", "eta_min_hours", "eta_max_hours", "cod_available", "is_active")
    list_filter = ("cod_available", "is_active", "state")
    search_fields = ("name", "code", "pincode_prefix", "city", "state")


class DeliveryEventInline(admin.TabularInline):
    model = DeliveryEvent
    extra = 0
    can_delete = False
    readonly_fields = ("status", "summary", "meta", "created_by", "created_at")


@admin.register(DeliveryShipment)
class DeliveryShipmentAdmin(admin.ModelAdmin):
    list_display = ("order", "carrier_name", "status", "tracking_reference", "service_level", "reattempt_count", "eta_end", "updated_at")
    list_filter = ("status", "service_level", "carrier_name")
    search_fields = ("order__order_number", "order__recipient", "tracking_reference", "carrier_name")
    readonly_fields = ("created_at", "updated_at", "assigned_at", "dispatched_at", "delivered_at", "failed_at")
    inlines = [DeliveryEventInline]


@admin.register(DeliveryEvent)
class DeliveryEventAdmin(admin.ModelAdmin):
    list_display = ("shipment", "status", "created_by", "created_at")
    list_filter = ("status",)
    search_fields = ("shipment__order__order_number", "summary")
    readonly_fields = ("shipment", "status", "summary", "meta", "created_by", "created_at")
