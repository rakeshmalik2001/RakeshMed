from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from platform_apps.catalog.models import Product

from .models import Cart, CartItem
from .serializers import CartReplaceSerializer, CartSerializer


def get_user_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


class CartDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = get_user_cart(request.user)
        return Response(CartSerializer(cart).data)


class CartReplaceView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        serializer = CartReplaceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cart = get_user_cart(request.user)
        payload_items = serializer.validated_data["items"]
        products = Product.objects.filter(slug__in=[item["slug"] for item in payload_items], is_active=True)
        product_map = {product.slug: product for product in products}

        with transaction.atomic():
            cart.items.all().delete()
            CartItem.objects.bulk_create(
                [
                    CartItem(
                        cart=cart,
                        product=product_map.get(item["slug"]),
                        product_slug=item["slug"],
                        name=item["name"],
                        meta=item["meta"],
                        off=item["off"],
                        mrp=item["mrp"],
                        sale_price=item["price"],
                        qty=item["qty"],
                        requires_prescription=item["rx"],
                    )
                    for item in payload_items
                ]
            )

        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)

