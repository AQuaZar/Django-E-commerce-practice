from django.urls import path
from .views import HomeView, ItemDetailView, checkout, detail, add_to_cart


app_name = "core"

urlpatterns = [
    path("", HomeView.as_view(), name="home-page"),
    path("checkout", checkout, name="checkout-page"),
    path("product/<slug>/", ItemDetailView.as_view(), name="product"),
    path("add-to-cart/<slug>", add_to_cart, name="add-to-cart"),
]

