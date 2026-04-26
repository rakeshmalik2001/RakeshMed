from django.urls import path

from .views import CartDetailView, CartReplaceView


urlpatterns = [
    path("", CartDetailView.as_view(), name="cart-detail"),
    path("replace/", CartReplaceView.as_view(), name="cart-replace"),
]

