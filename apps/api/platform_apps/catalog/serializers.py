from rest_framework import serializers

from .models import Brand, Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "description", "parent", "sort_order")


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ("id", "name", "slug", "description")


class ProductListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "sku",
            "category",
            "brand",
            "composition",
            "dosage_form",
            "strength",
            "pack_size",
            "manufacturer",
            "mrp",
            "sale_price",
            "requires_prescription",
            "is_otc",
            "stock_status",
        )


class ProductDetailSerializer(ProductListSerializer):
    substitutes = serializers.SerializerMethodField()

    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + (
            "description",
            "warnings",
            "side_effects",
            "storage_instructions",
            "substitutes",
        )

    def get_substitutes(self, obj):
        linked_products = [link.substitute_product for link in obj.substitute_links.select_related("substitute_product")]
        return ProductListSerializer(linked_products, many=True).data


class AdminProductSerializer(serializers.ModelSerializer):
    category_slug = serializers.SlugRelatedField(
        source="category",
        slug_field="slug",
        queryset=Category.objects.filter(is_active=True),
    )
    brand_slug = serializers.SlugRelatedField(
        source="brand",
        slug_field="slug",
        queryset=Brand.objects.filter(is_active=True),
        allow_null=True,
        required=False,
    )
    category = CategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "sku",
            "category",
            "category_slug",
            "brand",
            "brand_slug",
            "composition",
            "dosage_form",
            "strength",
            "pack_size",
            "manufacturer",
            "description",
            "warnings",
            "side_effects",
            "storage_instructions",
            "mrp",
            "sale_price",
            "requires_prescription",
            "is_otc",
            "is_active",
            "stock_status",
        )


class AdminInventoryProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    brand = BrandSerializer(read_only=True)

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
        )
