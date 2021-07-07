from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, View, DetailView
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from .models import Item, OrderItem, Order, BillingAddress, Payment, Coupon
from .forms import CheckoutForm

import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY


class CheckoutView(View):
    def get(self, *args, **kwargs):
        form = CheckoutForm()
        context = {"form": form}
        return render(self.request, "checkout-page.html", context)

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                street_address = form.cleaned_data.get("street_address")
                appartment_address = form.cleaned_data.get("appartment_address")
                country = form.cleaned_data.get("country")
                zip = form.cleaned_data.get("zip")
                # same_billing_address = form.cleaned_data.get("same_billing_address")
                # save_info = form.cleaned_data.get("save_info")
                payment_option = form.cleaned_data.get("payment_option")
                billing_address = BillingAddress(
                    user=self.request.user,
                    street_address=street_address,
                    appartment_address=appartment_address,
                    country=country,
                    zip=zip,
                )
                billing_address.save()
                order.billing_address = billing_address
                order.save()
                if payment_option == "S":
                    return redirect("core:payment", payment_option="stripe")
                elif payment_option == "P":
                    return redirect("core:payment", payment_option="paypal")
                else:
                    messages.error(self.request, "Invalid payment option")
                    return redirect("core:checkout-page")
        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order")
            return redirect("core:order-summary")


class PaymentView(View):
    def get(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        if order.billing_address:
            context = {
                "order": order,
                "DISPLAY_COUPON_FORM": False,
                "STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY,
            }
            return render(self.request, "payment.html", context)
        else:
            messages.warning(self.request, "You have not added a billing address")
            return redirect("core:checkout-page")
        return render(self.request, "payment.html")

    def post(self, *args, **kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        token = self.request.POST.get("stripeToken")
        print(token)
        amount = int(order.get_total_price()) * 100

        try:
            charge = stripe.Charge.create(amount=amount, currency="usd", source=token)
            print(charge)
            payment = Payment()
            payment.stripe_charge_id = charge["id"]
            payment.user = self.request.user
            payment.amount = amount
            payment.save()

            order_items = order.items.all()
            order_items.update(ordered=True)
            for item in order_items:
                item.save()

            order.ordered = True
            order.payment = payment
            order.save()

            messages.success(self.request, "Your order was successful")
            return redirect("/")
        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught

            body = e.json_body
            err = body.get("error", {})
            messages.warning(self.request, f"{err.get('message')}")
            return redirect("/")
        except stripe.error.RateLimitError as e:
            messages.error(self.request, "Rate limit error")
            return redirect("/")
            # Too many requests made to the API too quickly
        except stripe.error.InvalidRequestError as e:
            messages.error(self.request, "Invalid request")
            return redirect("/")
            # Invalid parameters were supplied to Stripe's API
        except stripe.error.AuthenticationError as e:
            messages.error(self.request, "Authentication error")
            return redirect("/")
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)

        except stripe.error.APIConnectionError as e:
            messages.error(self.request, "Api connection error")
            return redirect("/")
            # Network communication with Stripe failed

        except stripe.error.StripeError as e:
            messages.error(self.request, "Try again")
            return redirect("/")
            # Display a very generic error to the user, and maybe send
            # yourself an email

        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            messages.error(self.request, "??")
            return redirect("/")


def detail(reqest):
    return render(reqest, "product-page.html")


class HomeView(ListView):
    model = Item
    paginate_by = 10
    template_name = "home.html"


class OrderSummaryView(LoginRequiredMixin, View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            context = {"object": order}
            return render(self.request, "order_summary.html", context)

        except ObjectDoesNotExist:
            messages.error(self.request, "You do not have an active order")
            return redirect("/")


class ItemDetailView(DetailView):
    model = Item
    template_name = "product.html"


@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item, user=request.user, ordered=False
    )
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if order item in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(
                request,
                f"One more {item.title} was added to cart, there are {order_item.quantity} in total.",
            )
            return redirect("core:order-summary")
        else:
            order_item.quantity = 1
            order_item.save()
            messages.info(request, f"{item.title} was added to your cart")
            order.items.add(order_item)
            return redirect("core:order-summary")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, f"{item.title} was added to your cart")
        return redirect("core:order-summary")


@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if order item in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item, user=request.user, ordered=False
            )[0]
            order.items.remove(order_item)
            order_item.quantity = 0
            order_item.save()
            messages.info(request, f"{item.title} was removed from your cart")
            return redirect("core:order-summary")
        else:
            messages.info(request, f"{item.title} was not in your cart")
            return redirect("core:order-summary")
    else:
        messages.info(request, "No active order was found")
        return redirect("core:order-summary")


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if order item in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item, user=request.user, ordered=False
            )[0]
            if order_item.quantity != 1:
                order_item.quantity -= 1
                order_item.save()
                messages.info(request, f"{item.title} quantity was updated")
            return redirect("core:order-summary")
        else:
            messages.info(request, f"{item.title} was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "No active order was found")
        return redirect("core:product", slug=slug)


def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist")
        return redirect("core:checkout-page")


def add_coupon(request, code):
    try:
        order = Order.objects.get(user=request.user, ordered=False)
        order.coupon = get_coupon(request, code)
        order.save()
        messages.success(request, "Coupon accepted!")
        return redirect("core:checkout-page")
    except ObjectDoesNotExist:
        messages.info(request, "No active order was found")
        return redirect("core:checkout-page")
