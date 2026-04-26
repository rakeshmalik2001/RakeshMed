from django import forms
from django.contrib import admin
from django.db.models import Case, CharField, F, IntegerField, Value, When

from .models import Brand, Category, Product, ProductSubstitute


class NavbarCategoryFilter(admin.SimpleListFilter):
    title = "navbar"
    parameter_name = "navbar"

    def lookups(self, request, model_admin):
        root_categories = Category.objects.filter(parent__isnull=True).order_by("sort_order", "name")
        return [(category.pk, category.name) for category in root_categories]

    def queryset(self, request, queryset):
        value = self.value()
        if not value:
            return queryset
        return queryset.filter(pk=value) | queryset.filter(parent_id=value) | queryset.filter(parent__parent_id=value)


class CategorySelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        option_value = option.get("value")
        if option_value not in ("", None):
            try:
                raw_value = getattr(value, "value", option_value)
                category = self.choices.queryset.select_related("parent").get(pk=raw_value)
                option["attrs"]["data-navbar-id"] = str(category.parent_id or "")
            except (Category.DoesNotExist, TypeError, ValueError):
                option["attrs"]["data-navbar-id"] = ""
        return option


class CategoryAdminForm(forms.ModelForm):
    navbar_category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        required=False,
        label="Navbar",
        help_text="Choose the top-level navbar group.",
    )
    section_category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        required=False,
        label="Category",
        help_text="Choose the category under the selected navbar. Leave empty to create a navbar item.",
        widget=CategorySelect,
    )

    class Meta:
        model = Category
        fields = ("name", "slug", "description", "navbar_category", "section_category", "is_active", "sort_order")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        root_categories = Category.objects.filter(parent__isnull=True).order_by("sort_order", "name")
        all_section_categories = Category.objects.filter(parent__isnull=False, parent__parent__isnull=True).select_related("parent").order_by(
            "parent__sort_order",
            "parent__name",
            "sort_order",
            "name",
        )

        self.fields["navbar_category"].queryset = root_categories
        self.fields["section_category"].queryset = all_section_categories
        self.fields["section_category"].label_from_instance = lambda obj: f"{obj.parent.name} -> {obj.name}"

        instance = self.instance
        selected_navbar = None

        if self.is_bound:
            navbar_value = self.data.get("navbar_category")
            if navbar_value:
                try:
                    selected_navbar = int(navbar_value)
                except (TypeError, ValueError):
                    selected_navbar = None
        elif instance and instance.pk:
            if instance.depth == 0:
                selected_navbar = instance.pk
            elif instance.depth == 1:
                selected_navbar = instance.parent_id
            elif instance.depth >= 2:
                selected_navbar = instance.root_category.pk

        if selected_navbar:
            self.fields["section_category"].queryset = all_section_categories.filter(parent_id=selected_navbar)

        if not instance or not instance.pk:
            return

        if instance.depth == 0:
            self.initial["navbar_category"] = instance
        elif instance.depth == 1:
            self.initial["navbar_category"] = instance.parent
        elif instance.depth >= 2:
            self.initial["navbar_category"] = instance.root_category
            self.initial["section_category"] = instance.parent

    def clean(self):
        cleaned_data = super().clean()
        navbar_category = cleaned_data.get("navbar_category")
        section_category = cleaned_data.get("section_category")

        if section_category and navbar_category and section_category.parent_id != navbar_category.id:
            self.add_error("section_category", "Selected category does not belong to the chosen navbar.")

        return cleaned_data


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryAdminForm
    save_on_top = True
    list_per_page = 25
    list_display = (
        "tree_name",
        "slug",
        "navbar_name",
        "parent",
        "hierarchy_path_display",
        "depth_display",
        "is_active",
        "sort_order",
    )
    list_filter = ("is_active", NavbarCategoryFilter, "parent")
    search_fields = ("name", "slug", "parent__name", "parent__parent__name")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("hierarchy_path_display", "navbar_name", "depth_display")
    fieldsets = (
        ("Category Details", {"fields": ("name", "slug", "description")}),
        ("Navigation Placement", {"fields": ("navbar_category", "section_category")}),
        ("Visibility and Order", {"fields": ("is_active", "sort_order")}),
        ("Hierarchy Summary", {"fields": ("hierarchy_path_display", "navbar_name", "depth_display")}),
    )

    class Media:
        js = ("catalog/admin/category-form.js",)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return (
            queryset.select_related("parent", "parent__parent")
            .annotate(
                depth_order=Case(
                    When(parent__isnull=True, then=Value(0)),
                    When(parent__parent__isnull=True, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                ),
                root_sort_order=Case(
                    When(parent__isnull=True, then=F("sort_order")),
                    When(parent__parent__isnull=True, then=F("parent__sort_order")),
                    default=F("parent__parent__sort_order"),
                    output_field=IntegerField(),
                ),
                root_name_order=Case(
                    When(parent__isnull=True, then=F("name")),
                    When(parent__parent__isnull=True, then=F("parent__name")),
                    default=F("parent__parent__name"),
                    output_field=CharField(),
                ),
                branch_sort_order=Case(
                    When(parent__isnull=True, then=Value(-1)),
                    When(parent__parent__isnull=True, then=F("sort_order")),
                    default=F("parent__sort_order"),
                    output_field=IntegerField(),
                ),
                branch_name_order=Case(
                    When(parent__isnull=True, then=Value("")),
                    When(parent__parent__isnull=True, then=F("name")),
                    default=F("parent__name"),
                    output_field=CharField(),
                ),
            )
            .order_by(
                "root_sort_order",
                "root_name_order",
                "branch_sort_order",
                "branch_name_order",
                "depth_order",
                "sort_order",
                "name",
            )
        )

    @admin.display(description="Name", ordering="name")
    def tree_name(self, obj: Category) -> str:
        prefix = ""
        if obj.depth == 1:
            prefix = "  |- "
        elif obj.depth >= 2:
            prefix = "    |- "
        return f"{prefix}{obj.name}"

    @admin.display(description="Navbar")
    def navbar_name(self, obj: Category) -> str:
        return obj.root_category.name

    @admin.display(description="Hierarchy")
    def hierarchy_path_display(self, obj: Category) -> str:
        return obj.hierarchy_path

    @admin.display(description="Level")
    def depth_display(self, obj: Category) -> int:
        return obj.depth

    def save_model(self, request, obj, form, change):
        navbar_category = form.cleaned_data.get("navbar_category")
        section_category = form.cleaned_data.get("section_category")

        if section_category is not None:
            obj.parent = section_category
        elif navbar_category is not None:
            if change and obj.pk == navbar_category.pk:
                obj.parent = None
            else:
                obj.parent = navbar_category
        else:
            obj.parent = None

        super().save_model(request, obj, form, change)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_display = ("name", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        ("Brand Details", {"fields": ("name", "slug", "description")}),
        ("Visibility", {"fields": ("is_active",)}),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_select_related = ("category", "brand")
    list_display = (
        "name",
        "sku",
        "category",
        "brand",
        "sale_price",
        "requires_prescription",
        "stock_status",
        "is_active",
    )
    list_filter = ("requires_prescription", "is_otc", "stock_status", "is_active", "category", "brand")
    search_fields = ("name", "sku", "slug", "composition", "manufacturer")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("Product Basics", {"fields": ("name", "slug", "sku", "category", "brand", "manufacturer")}),
        ("Composition", {"fields": ("composition", "dosage_form", "strength", "pack_size")}),
        ("Pricing", {"fields": ("mrp", "sale_price")}),
        ("Availability", {"fields": ("stock_status", "is_active", "requires_prescription", "is_otc")}),
        ("Content", {"fields": ("description", "warnings", "side_effects", "storage_instructions")}),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(ProductSubstitute)
class ProductSubstituteAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 25
    list_display = ("source_product", "substitute_product", "reason", "created_at")
    search_fields = ("source_product__name", "substitute_product__name", "reason")
    autocomplete_fields = ("source_product", "substitute_product")
    readonly_fields = ("created_at",)
    fieldsets = (
        ("Substitution Link", {"fields": ("source_product", "substitute_product", "reason")}),
        ("Audit", {"fields": ("created_at",)}),
    )
