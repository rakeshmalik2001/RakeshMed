from django.urls import path

from .views import (
    AdminInventoryDetailView,
    AdminInventoryListView,
    AdminProductDetailView,
    AdminProductListCreateView,
    BrandListView,
    CategoryListView,
    ProductDetailView,
    ProductListView,
)


urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="catalog-categories"),
    path("brands/", BrandListView.as_view(), name="catalog-brands"),
    path("products/", ProductListView.as_view(), name="catalog-products"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="catalog-product-detail"),
    path("admin/products/", AdminProductListCreateView.as_view(), name="admin-catalog-products"),
    path("admin/products/<int:pk>/", AdminProductDetailView.as_view(), name="admin-catalog-product-detail"),
    path("admin/inventory/", AdminInventoryListView.as_view(), name="admin-catalog-inventory"),
    path("admin/inventory/<int:pk>/", AdminInventoryDetailView.as_view(), name="admin-catalog-inventory-detail"),
]
