from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ("product_slug", "name", "qty", "sale_price", "requires_prescription", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "updated_at")
    list_select_related = ("user",)
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Cart Details", {"fields": ("user",)}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )
    list_per_page = 25
    inlines = [CartItemInline]


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_select_related = ("cart", "cart__user", "product")
    list_display = ("product_slug", "cart", "qty", "requires_prescription", "updated_at")
    list_filter = ("requires_prescription",)
    search_fields = ("product_slug", "name", "cart__user__phone_number")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Cart Item", {"fields": ("cart", "product", "product_slug", "name", "meta", "off")}),
        ("Pricing and Quantity", {"fields": ("mrp", "sale_price", "qty", "requires_prescription")}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )
