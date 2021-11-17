from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django import forms
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.models import User
from .forms import (
    RegisterUserForm,
    LoginUserForm,
    CreateNewProduct,
    EditProductForm,
    BuyProductsForm,
)
import stripe
from niki_shop.settings import STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY
from .models import StripeData, Product, BuyProducts
from asgiref.sync import sync_to_async, async_to_sync


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
        n = stripe.Account.retrieve(stripe_data.stripe_id, STRIPE_SECRET_KEY)
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
    stripe_user = stripe.Account.retrieve(stripe_id, STRIPE_SECRET_KEY)
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
    if stripe_id is not None:
        stripe_user = stripe.Account.retrieve(stripe_id, STRIPE_SECRET_KEY)
        if not stripe_user.charges_enabled and not stripe_user.details_submitted:
            n = stripe.AccountLink.create(
                account=stripe_user.id,
                refresh_url="http://localhost:8000/shop/create_stripe_account/",
                return_url="http://localhost:8000/shop/home/",
                type='account_onboarding',
            )
            # return redirect("home")
            return redirect(n.url)
        raise ValueError("You already have stripe account")
    try:
        stripe.api_key = STRIPE_SECRET_KEY
        user_stripe_account = stripe.Account.create(
            type="standard",
            country="BG",
            email=user.email,

        )
        messages.success(request, "user_stripe_account")
        stripe_data = StripeData(user=user, stripe_id=user_stripe_account.id)
        stripe_data.save()

        n = stripe.AccountLink.create(
            account=user_stripe_account.id,
            refresh_url="http://localhost:8000/shop/create_stripe_account/",
            return_url="http://localhost:8000/shop/home/",
            type='account_onboarding',
        )
        # return redirect("home")
        return redirect(n.url)

    except Exception as e:
        messages.success(request, e)
        return redirect("home")


def create_product(request):
    user = get_session_user(request)
    check_stripe_id(user)
    form = CreateNewProduct(request.POST or None, user=user)
    if request.method == "POST":
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Your product is Successful created")
                return redirect("home")
            except forms.ValidationError as e:
                form.add_error(field=None, error=e)

    return render(request, "shop/create_product.html", {"form": form})


def edit_product(request, product_id):
    user = get_session_user(request)
    check_stripe_id(user)
    product = get_object_or_404(Product, id=product_id)
    if not product.user_id == user.id:
        raise ValueError("Not your product")
    initial = [('name', product.name),
               ('description', product.description),
               ('price', product.price),
               ('currency', product.currency),
               ('total_quantity', product.total_quantity)]
    form = EditProductForm(request.POST or None, instance=product, product_id=product_id)
    if request.method == "POST":
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Your product is Successful edited")
                return redirect("home")
            except forms.ValidationError as e:
                form.add_error(field=None, error=e)

    return render(request, "shop/edit_product.html", {"form": form, "product": product})


def detail_product(request, product_id):
    user = get_session_user(request)
    check_stripe_id(user)
    product = get_object_or_404(Product, id=product_id)
    if product.user_id == user.id:
        can_pay = None
    else:
        can_pay = True
    form = BuyProductsForm(request.POST or None, product=product, user=user)
    if request.method == "POST":
        if form.is_valid():
            try:
                if product.product_stripe_id:
                    price = stripe.Price.list(product=product.product_stripe_id)
                else:
                    stripe_product = stripe.Product.create(name=product.name,
                                                           description=product.description,
                                                           )
                    price = stripe.Price.create(unit_amount=int(product.price) * 100,
                                                currency=product.currency,
                                                product=stripe_product.id)
                    product.product_stripe_id = stripe_product.id
                    product.save()

                checkout_session = stripe.checkout.Session.create(
                    line_items=[
                        {
                            # Provide the exact Price ID (e.g. pr_1234) of the product you want to sell
                            'price': price.id,
                            'quantity': form.cleaned_data["total_quantity"],
                        },
                    ],
                    payment_method_types=[
                        'card',
                    ],
                    mode='payment',
                    success_url="http://localhost:8000/shop/home/",
                    cancel_url="http://localhost:8000/shop/login/",
                )

            except Exception as e:
                return str(e)
            try:
                form.save()
                messages.success(request, "You Successful buy")
                # return redirect("home")
                return redirect(checkout_session.url, code=303)
            except forms.ValidationError as e:
                form.add_error(field=None, error=e)
    return render(request, "shop/detail_product.html", {"product": product, "can_pay": can_pay, "form": form})


def delete_product(request, product_id):
    user = get_session_user(request)
    check_stripe_id(user)
    product = get_object_or_404(Product, id=product_id)
    if not product.user_id == user.id:
        raise ValueError("Not your product")
    # stripe.Product.delete(product.product_stripe_id)
    product.delete()
    return HttpResponseRedirect(reverse("home"))
