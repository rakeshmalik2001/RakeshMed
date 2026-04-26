from django.contrib.postgres.indexes import GinIndex
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "name"]

    @property
    def depth(self) -> int:
        depth = 0
        current = self.parent
        while current is not None:
            depth += 1
            current = current.parent
        return depth

    @property
    def root_category(self) -> "Category":
        current = self
        while current.parent is not None:
            current = current.parent
        return current

    @property
    def hierarchy_names(self) -> list[str]:
        names: list[str] = []
        current: Category | None = self
        while current is not None:
            names.append(current.name)
            current = current.parent
        return list(reversed(names))

    @property
    def hierarchy_path(self) -> str:
        return " -> ".join(self.hierarchy_names)

    def __str__(self) -> str:
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    STOCK_STATUS_CHOICES = (
        ("in_stock", "In Stock"),
        ("low_stock", "Low Stock"),
        ("out_of_stock", "Out of Stock"),
    )

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    sku = models.CharField(max_length=64, unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name="products", null=True, blank=True)
    manufacturer = models.CharField(max_length=255, blank=True)
    composition = models.CharField(max_length=255, blank=True)
    dosage_form = models.CharField(max_length=120, blank=True)
    strength = models.CharField(max_length=120, blank=True)
    pack_size = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    warnings = models.TextField(blank=True)
    side_effects = models.TextField(blank=True)
    storage_instructions = models.TextField(blank=True)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    requires_prescription = models.BooleanField(default=False)
    is_otc = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    stock_status = models.CharField(max_length=20, choices=STOCK_STATUS_CHOICES, default="in_stock")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["sku"]),
            models.Index(fields=["requires_prescription", "is_active"]),
            models.Index(fields=["stock_status", "is_active"]),
            GinIndex(fields=["name"], name="catalog_product_name_trgm", opclasses=["gin_trgm_ops"]),
            GinIndex(fields=["composition"], name="catalog_product_comp_trgm", opclasses=["gin_trgm_ops"]),
            GinIndex(fields=["manufacturer"], name="catalog_product_manu_trgm", opclasses=["gin_trgm_ops"]),
            GinIndex(fields=["sku"], name="catalog_product_sku_trgm", opclasses=["gin_trgm_ops"]),
        ]

    def __str__(self) -> str:
        return self.name


class ProductSubstitute(models.Model):
    source_product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="substitute_links")
    substitute_product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="substitute_for_links")
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("source_product", "substitute_product")
        verbose_name = "Product Substitute"
        verbose_name_plural = "Product Substitutes"

    def __str__(self) -> str:
        return f"{self.source_product} -> {self.substitute_product}"
