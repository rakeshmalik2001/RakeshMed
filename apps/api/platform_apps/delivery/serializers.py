from rest_framework import serializers

from .models import DeliveryEvent, DeliveryShipment, DeliveryZone
from .services import delivery_blockers_for_order, is_dispatch_ready, serviceability_snapshot


class DeliveryZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryZone
        fields = (
            "id",
            "name",
            "code",
            "pincode_prefix",
            "city",
            "state",
            "eta_min_hours",
            "eta_max_hours",
            "cod_available",
            "is_active",
        )


class DeliveryEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryEvent
        fields = ("status", "summary", "meta", "actor_name", "created_at")

    def get_actor_name(self, obj: DeliveryEvent) -> str:
        if obj.created_by:
            return obj.created_by.full_name or obj.created_by.phone_number
        return "System"


class DeliveryShipmentSerializer(serializers.ModelSerializer):
    zone = DeliveryZoneSerializer(read_only=True)
    events = DeliveryEventSerializer(many=True, read_only=True)
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    recipient = serializers.CharField(source="order.recipient", read_only=True)
    city = serializers.CharField(source="order.city", read_only=True)
    pincode = serializers.CharField(source="order.pincode", read_only=True)
    is_dispatch_ready = serializers.SerializerMethodField()
    dispatch_blockers = serializers.SerializerMethodField()
    eta_label = serializers.SerializerMethodField()

    class Meta:
        model = DeliveryShipment
        fields = (
            "id",
            "order_number",
            "recipient",
            "city",
            "pincode",
            "carrier_name",
            "service_level",
            "status",
            "is_dispatch_ready",
            "dispatch_blockers",
            "eta_label",
            "tracking_reference",
            "status_notes",
            "failure_reason",
            "reattempt_count",
            "eta_start",
            "eta_end",
            "next_attempt_at",
            "assigned_at",
            "dispatched_at",
            "delivered_at",
            "failed_at",
            "updated_at",
            "zone",
            "events",
        )

    def get_is_dispatch_ready(self, obj: DeliveryShipment) -> bool:
        return is_dispatch_ready(obj.order, zone=obj.zone)

    def get_dispatch_blockers(self, obj: DeliveryShipment) -> list[str]:
        return delivery_blockers_for_order(obj.order, zone=obj.zone)

    def get_eta_label(self, obj: DeliveryShipment) -> str:
        if obj.zone:
            return f"{obj.zone.eta_min_hours}-{obj.zone.eta_max_hours} hours"
        return ""


class DeliveryShipmentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryShipment
        fields = ("carrier_name", "service_level", "status", "tracking_reference", "status_notes", "failure_reason", "next_attempt_at")


class ServiceabilitySerializer(serializers.Serializer):
    pincode = serializers.CharField()
    is_serviceable = serializers.BooleanField()
    cod_available = serializers.BooleanField()
    zone = serializers.JSONField(allow_null=True)
    eta_label = serializers.CharField()
    eta_start = serializers.DateTimeField(required=False, allow_null=True)
    eta_end = serializers.DateTimeField(required=False, allow_null=True)

    @classmethod
    def from_pincode(cls, pincode: str):
        return cls(serviceability_snapshot(pincode))
