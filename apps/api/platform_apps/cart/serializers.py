from decimal import Decimal

from rest_framework import serializers

from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    slug = serializers.CharField(source="product_slug")
    price = serializers.DecimalField(source="sale_price", max_digits=10, decimal_places=2)
    rx = serializers.BooleanField(source="requires_prescription")

    class Meta:
        model = CartItem
        fields = ("slug", "name", "off", "mrp", "price", "meta", "rx", "qty")


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    item_count = serializers.SerializerMethodField()
    requires_prescription_count = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()
    delivery = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = (
            "items",
            "item_count",
            "requires_prescription_count",
            "subtotal",
            "discount",
            "delivery",
            "total",
        )

    def _item_queryset(self, obj: Cart):
        return obj.items.all()

    def get_item_count(self, obj: Cart):
        return sum(item.qty for item in self._item_queryset(obj))

    def get_requires_prescription_count(self, obj: Cart):
        return sum(item.qty for item in self._item_queryset(obj) if item.requires_prescription)

    def get_subtotal(self, obj: Cart):
        return sum(Decimal(item.mrp) * item.qty for item in self._item_queryset(obj))

    def get_discount(self, obj: Cart):
        subtotal = self.get_subtotal(obj)
        discounted = sum(Decimal(item.sale_price) * item.qty for item in self._item_queryset(obj))
        return subtotal - discounted

    def get_delivery(self, obj: Cart):
        return Decimal("40.00") if self._item_queryset(obj).exists() else Decimal("0.00")

    def get_total(self, obj: Cart):
        discounted = sum(Decimal(item.sale_price) * item.qty for item in self._item_queryset(obj))
        return discounted + self.get_delivery(obj)


class CartReplaceItemInputSerializer(serializers.Serializer):
    slug = serializers.SlugField(max_length=255)
    name = serializers.CharField(max_length=255)
    off = serializers.CharField(max_length=32, allow_blank=True, required=False, default="")
    mrp = serializers.DecimalField(max_digits=10, decimal_places=2)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    meta = serializers.CharField(max_length=255, allow_blank=True, required=False, default="")
    rx = serializers.BooleanField(default=False)
    qty = serializers.IntegerField(min_value=1)


class CartReplaceSerializer(serializers.Serializer):
    items = CartReplaceItemInputSerializer(many=True)

