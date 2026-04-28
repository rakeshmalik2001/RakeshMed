from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers

from platform_apps.audit.services import record_audit_event
from platform_apps.catalog.serializers import BrandSerializer, CategorySerializer
from platform_apps.catalog.models import Product

from .models import InventoryItem, LowStockRule, StockLocation, StockMovement
from .services import get_default_location, refresh_product_stock_status


class StockLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockLocation
        fields = ("id", "name", "code", "kind", "is_active")


class InventoryLocationItemSerializer(serializers.ModelSerializer):
    location = StockLocationSerializer(read_only=True)
    available_quantity = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = (
            "id",
            "location",
            "quantity_on_hand",
            "reserved_quantity",
            "inbound_quantity",
            "available_quantity",
            "updated_at",
        )

    def get_available_quantity(self, obj: InventoryItem) -> int:
        return obj.available_quantity


class InventorySummarySerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    total_on_hand = serializers.SerializerMethodField()
    total_reserved = serializers.SerializerMethodField()
    total_available = serializers.SerializerMethodField()
    low_stock_threshold = serializers.SerializerMethodField()
    location_items = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "sku",
            "category",
            "brand",
            "manufacturer",
            "pack_size",
            "requires_prescription",
            "is_active",
            "stock_status",
            "mrp",
            "sale_price",
            "updated_at",
            "total_on_hand",
            "total_reserved",
            "total_available",
            "low_stock_threshold",
            "location_items",
        )

    def _get_totals(self, obj: Product) -> dict[str, int]:
        if hasattr(obj, "_inventory_totals_cache"):
            return obj._inventory_totals_cache
        totals = obj.inventory_items.aggregate(
            total_on_hand=Sum("quantity_on_hand"),
            total_reserved=Sum("reserved_quantity"),
        )
        result = {
            "total_on_hand": totals.get("total_on_hand") or 0,
            "total_reserved": totals.get("total_reserved") or 0,
        }
        result["total_available"] = result["total_on_hand"] - result["total_reserved"]
        obj._inventory_totals_cache = result
        return result

    def get_total_on_hand(self, obj: Product) -> int:
        return self._get_totals(obj)["total_on_hand"]

    def get_total_reserved(self, obj: Product) -> int:
        return self._get_totals(obj)["total_reserved"]

    def get_total_available(self, obj: Product) -> int:
        return self._get_totals(obj)["total_available"]

    def get_low_stock_threshold(self, obj: Product) -> int:
        if hasattr(obj, "low_stock_rule"):
            return obj.low_stock_rule.threshold_quantity
        return 5

    def get_location_items(self, obj: Product):
        items = obj.inventory_items.select_related("location").order_by("location__sort_order", "location__name")
        return InventoryLocationItemSerializer(items, many=True).data


class InventoryAdjustmentSerializer(serializers.Serializer):
    location_id = serializers.PrimaryKeyRelatedField(
        queryset=StockLocation.objects.filter(is_active=True),
        required=False,
        allow_null=True,
        source="location",
    )
    quantity_delta = serializers.IntegerField(required=False)
    quantity_on_hand = serializers.IntegerField(required=False)
    reserved_quantity = serializers.IntegerField(required=False, min_value=0)
    inbound_quantity = serializers.IntegerField(required=False, min_value=0)
    threshold_quantity = serializers.IntegerField(required=False, min_value=0)
    is_active = serializers.BooleanField(required=False)
    reference = serializers.CharField(required=False, allow_blank=True, max_length=120)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=255)
    movement_type = serializers.ChoiceField(
        choices=StockMovement.MOVEMENT_CHOICES,
        required=False,
        default="adjustment",
    )

    def validate(self, attrs):
        if not any(
            key in attrs
            for key in ("quantity_delta", "quantity_on_hand", "reserved_quantity", "inbound_quantity", "threshold_quantity", "is_active")
        ):
            raise serializers.ValidationError("Provide at least one inventory or publish-state change.")
        return attrs

    def update(self, instance: Product, validated_data):
        location = validated_data.pop("location", None) or get_default_location()
        quantity_delta = validated_data.pop("quantity_delta", None)
        quantity_on_hand = validated_data.pop("quantity_on_hand", None)
        reserved_quantity = validated_data.pop("reserved_quantity", None)
        inbound_quantity = validated_data.pop("inbound_quantity", None)
        threshold_quantity = validated_data.pop("threshold_quantity", None)
        is_active = validated_data.pop("is_active", None)
        reference = validated_data.pop("reference", "")
        notes = validated_data.pop("notes", "")
        movement_type = validated_data.pop("movement_type", "adjustment")

        with transaction.atomic():
            inventory_item = (
                InventoryItem.objects.select_for_update()
                .filter(product=instance, location=location)
                .first()
            )
            previous_quantity = inventory_item.quantity_on_hand if inventory_item else 0
            next_quantity_on_hand = previous_quantity
            next_reserved_quantity = inventory_item.reserved_quantity if inventory_item else 0
            next_inbound_quantity = inventory_item.inbound_quantity if inventory_item else 0

            if quantity_on_hand is not None:
                next_quantity_on_hand = quantity_on_hand
            elif quantity_delta is not None:
                next_quantity_on_hand = previous_quantity + quantity_delta

            if next_quantity_on_hand < 0:
                raise serializers.ValidationError({"quantity_on_hand": "Quantity on hand cannot be negative."})

            if reserved_quantity is not None:
                next_reserved_quantity = reserved_quantity
            if inbound_quantity is not None:
                next_inbound_quantity = inbound_quantity

            if next_reserved_quantity > max(next_quantity_on_hand + next_inbound_quantity, 0):
                raise serializers.ValidationError({"reserved_quantity": "Reserved quantity cannot exceed available plus inbound stock."})

            if inventory_item is None:
                inventory_item = InventoryItem(
                    product=instance,
                    location=location,
                    quantity_on_hand=0,
                    reserved_quantity=0,
                    inbound_quantity=0,
                )

            inventory_item.quantity_on_hand = next_quantity_on_hand
            inventory_item.reserved_quantity = next_reserved_quantity
            inventory_item.inbound_quantity = next_inbound_quantity

            inventory_item.save()

            final_delta = inventory_item.quantity_on_hand - previous_quantity
            if final_delta:
                StockMovement.objects.create(
                    product=instance,
                    inventory_item=inventory_item,
                    location=location,
                    movement_type=movement_type,
                    quantity_delta=final_delta,
                    reference=reference,
                    notes=notes,
                    created_by=self.context["request"].user,
                )

            if threshold_quantity is not None:
                low_stock_rule, _rule_created = LowStockRule.objects.get_or_create(product=instance)
                low_stock_rule.threshold_quantity = threshold_quantity
                low_stock_rule.location = None
                low_stock_rule.save()

            if is_active is not None:
                instance.is_active = is_active
                instance.save(update_fields=["is_active", "updated_at"])

            instance.refresh_from_db()
            refresh_product_stock_status(instance)
            record_audit_event(
                actor=self.context["request"].user,
                event_type="inventory_adjusted",
                entity_type="product",
                entity_id=instance.id,
                severity="warning" if instance.stock_status in {"low_stock", "out_of_stock"} else "info",
                message=f"Inventory adjusted for {instance.name}.",
                meta={
                    "location_code": location.code,
                    "movement_type": movement_type,
                    "quantity_delta": final_delta,
                    "quantity_on_hand": inventory_item.quantity_on_hand,
                    "reserved_quantity": inventory_item.reserved_quantity,
                    "stock_status": instance.stock_status,
                    "reference": reference,
                },
            )

        return instance
