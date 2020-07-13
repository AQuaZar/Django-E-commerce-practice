from django.shortcuts import render
from .models import Item, OrderItem, Order


def home_page(reqest):
    return render(reqest, "home-page.html")


def checkout(reqest):
    return render(reqest, "checkout-page.html")


def detail(reqest):
    return render(reqest, "product-page.html")

