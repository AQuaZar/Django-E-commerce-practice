from django.shortcuts import render
from .models import Item, OrderItem, Order


def item_list(reqest):
    context = {"items": Item.objects.all()}
    return render(reqest, "home-page.html", context)
