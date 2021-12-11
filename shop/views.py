import stripe

from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.models import User
from .forms import (
    RegisterUserForm,
    LoginUserForm,
    ProductForm,
    BuyProductsForm,
)
from .models import StripeData, Product, ProductPurchase


def get_session_user(request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise ValueError("You are not logged or don't have permission")
    else:
        user = User.objects.get(pk=user_id)
        return user


def check_stripe_id(user):
    # user = get_session_user(request)
    try:
        stripe_data = StripeData.objects.get(user=user)
        n = stripe.Account.retrieve(stripe_data.stripe_id, settings.STRIPE_SECRET_KEY)
        stripe_id = n.id
    except Exception:
        stripe_id = None
    return stripe_id


def my_products(user):
    check_stripe_id(user)
    products = list(user.product_set.all())
    return products


def others_products(user):
    check_stripe_id(user)
    products = list(Product.objects.exclude(user=user))
    return products


def purchased_products(user):
    check_stripe_id(user)
    products = list(user.buyproducts_set.all())
    return products


def sell_products(user):
    check_stripe_id(user)
    products = list()
    for p in user.product_set.all():
        for n in p.buyproducts_set.all():
            if n is not None:
                products.append(n)
    return products


# Create your views here.
def index(request):
    return render(request, "shop/index.html")


def register(request):
    form = RegisterUserForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            try:
                form.save(request)
                messages.success(request, "Your registration is Successful")
                return redirect("home")
            except forms.ValidationError as e:
                form.add_error(field=None, error=e)

    return render(request, "shop/register.html", {"form": form})


def login(request):
    form = LoginUserForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            try:
                form.save(request)
                messages.success(request, "Welcome back")
                return redirect("home")
            except forms.ValidationError as e:
                form.add_error(field=None, error=e)

    return render(request, "shop/login.html", {"form": form})


def logout(request):
    if get_session_user(request):
        del request.session["user_id"]

        return HttpResponseRedirect(reverse("index"))


def home(request):
    user = get_session_user(request)
    stripe_id = check_stripe_id(user)
    products_my = my_products(user)
    products_others = others_products(user)
    products_purchased = purchased_products(user)
    products_sell = sell_products(user)
    stripe_user = stripe.Account.retrieve(stripe_id, settings.STRIPE_SECRET_KEY)
    return render(
        request,
        "shop/home.html",
        {
            "user": user,
            "stripe": stripe_id,
            "my_products": products_my,
            "others_products": products_others,
            "stripe_user": stripe_user,
            "purchased_products": products_purchased,
            "sell_products": products_sell,
        },
    )


def register_in_stripe(request):
    user = get_session_user(request)
    stripe_id = check_stripe_id(user)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    if not stripe_id:
        try:
            user_stripe_account = stripe.Account.create(
                type="standard",
                country="BG",
                email=user.email,
            )
            stripe_id = user_stripe_account.id

            messages.success(request, "user_stripe_account")
            stripe_data = StripeData(user=user, stripe_id=stripe_id)
            stripe_data.save()
        except Exception as e:
            messages.error(request, f"Failed to create stripe account got: {e}")
            return redirect("home")

    stripe_user = stripe.Account.retrieve(stripe_id, settings.STRIPE_SECRET_KEY)

    if stripe_user.charges_enabled and stripe_user.details_submitted:
        messages.success(request, "You already have an stripe account")
        return redirect("home")

    n = stripe.AccountLink.create(
        account=stripe_user.id,
        refresh_url="http://localhost:8000/shop/create_stripe_account/",
        return_url="http://localhost:8000/shop/home/",
        type="account_onboarding",
    )
    return redirect(n.url)


def create_product(request):
    user = get_session_user(request)
    check_stripe_id(user)
    form = ProductForm(request.POST or None, user=user)
    if request.method == "POST":
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Your product is Successful created")
                return redirect("home")
            except Exception as e:
                form.add_error(None, f"Something Unexpected happen: {e}")

    return render(request, "shop/create_product.html", {"form": form})


def edit_product(request, product_id):
    user = get_session_user(request)
    check_stripe_id(user)
    product = get_object_or_404(user.product_set.all(), id=product_id)

    form = ProductForm(request.POST or None, instance=product)
    if request.method == "POST":
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Your product is Successful edited")
                return redirect("home")
            except Exception as e:
                form.add_error(None, f"Something Unexpected happen: {e}")

    return render(request, "shop/edit_product.html", {"form": form, "product": product})


def detail_product(request, product_id):
    user = get_session_user(request)
    product = get_object_or_404(Product, id=product_id)
    payer_stripe_id = check_stripe_id(product.user)
    can_pay = (user.id != product.user_id) and payer_stripe_id

    form = BuyProductsForm(request.POST or None, product=product, user=user)
    if request.method == "POST":
        if form.is_valid():
            try:
                purchase = form.save()

                # https://stripe.com/docs/connect/enable-payment-acceptance-guide?platform=web&elements-or-checkout=checkout#web-return-url
                checkout_session = stripe.checkout.Session.create(
                    stripe_account=payer_stripe_id,
                    line_items=[
                        {
                            "price_data": {
                                "product_data": {
                                    "name": product.name,
                                    "description": product.description,
                                    "metadata": {"product_id": product.id},
                                },
                                "unit_amount": product.price,
                                "currency": product.currency,
                            },
                            "quantity": form.cleaned_data["total_quantity"],
                        },
                    ],
                    payment_intent_data={
                        "application_fee_amount": 100,
                    },
                    payment_method_types=[
                        "card",
                    ],
                    metadata={
                        "purchase_id": purchase.id,
                    },
                    mode="payment",
                    success_url=f"http://localhost:8000/shop/success/?purchase_id={purchase.id}",
                    cancel_url="http://localhost:8000/shop/login/",
                )
            except Exception as e:
                form.add_error(None, f"Something Unexpected happen: {e}")
            else:
                return redirect(checkout_session.url, code=303)

    return render(
        request,
        "shop/detail_product.html",
        {"product": product, "can_pay": can_pay, "form": form},
    )


def delete_product(request, product_id):
    user = get_session_user(request)
    product = get_object_or_404(user.product_set.all(), id=product_id)
    product.delete()
    messages.success(request, "product has been deleted")
    return redirect("home")


def webhook_received(request):
    if not request.method == "POST":
        return HttpResponse(status=400)

    # Verify webhook signature and extract the event.
    # See https://stripe.com/docs/webhooks/signatures for more information.
    try:
        event = stripe.Webhook.construct_event(
            payload=request.body,  # request_data
            sig_header=request.META.get("HTTP_STRIPE_SIGNATURE"),
            secret=settings.STRIPE_ENDPOINT_SECRET,
        )
    except ValueError:
        # Invalid payload.
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Invalid Signature.
        return HttpResponse(status=400)

    if event.type == "checkout.session.completed":
        session = event.data.object
        handle_completed_checkout_session(session)

    return HttpResponse(status=200)


def handle_completed_checkout_session(session):
    purchase_id = session.metadata.get("purchase_id")
    purchase = ProductPurchase.objects.get(id=purchase_id)
    purchase.completed = True
    purchase.save()
