from django.urls import path
from .views import home_page, checkout, detail


app_name = "core"

urlpatterns = [
    path("", home_page, name="home-page"),
    path("checkout", checkout, name="checkout-page"),
    path("detail", detail, name="product-detail"),
]

