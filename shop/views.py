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
)
import stripe
from niki_shop.settings import STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY
from .models import StripeData, Product
from asgiref.sync import sync_to_async, async_to_sync


def get_session_user(request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise ValueError("You are not logged or don't have permission")
    else:
        user = User.objects.get(pk=user_id)
        return user


def check_stripe_id(request):
    user = get_session_user(request)
    try:
        stripe_data = StripeData.objects.get(user=user)
        n = stripe.Account.retrieve(stripe_data.stripe_id, STRIPE_SECRET_KEY)
        stripe_id = n.id
    except Exception:
        stripe_id = None
    return stripe_id


def my_products(request):
    user = get_session_user(request)
    check_stripe_id(request)
    products = list(user.product_set.all())
    return products


def others_products(request):
    user = get_session_user(request)
    check_stripe_id(request)
    products = list(Product.objects.exclude(user=user))
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
    stripe_id = check_stripe_id(request)
    products_my = my_products(request)
    products_others = others_products(request)
    return render(
        request,
        "shop/home.html",
        {
            "user": user,
            "stripe": stripe_id,
            "my_products": products_my,
            "others_products": products_others,
        },
    )


def register_in_stripe(request):
    user = get_session_user(request)
    stripe_id = check_stripe_id(request)
    if stripe_id is not None:
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
            return_url="http://localhost:8000/shop/login/",
            type='account_onboarding',
        )
        return redirect("home")

    except Exception as e:
        messages.success(request, e)
        return redirect("home")


def create_product(request):
    user = get_session_user(request)
    check_stripe_id(request)
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
    check_stripe_id(request)
    product = get_object_or_404(Product, id=product_id)
    if not product.user_id == user.id:
        raise ValueError("Not your product")
    initial = [('name', product.name),
               ('description', product.description),
               ('price', product.price),
               ('currency', product.currency),
               ('total_quantity', product.total_quantity)]
    form = EditProductForm(request.POST or None, initial=initial, product_id=product_id)
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
    check_stripe_id(request)
    product = get_object_or_404(Product, id=product_id)
    """if product.user_id == user.id:
        can_pay = None
    else:
        can_pay = True"""
    return render(request, "shop/detail_product.html", {"product": product})


def delete_product(request, product_id):
    user = get_session_user(request)
    check_stripe_id(request)
    product = get_object_or_404(Product, id=product_id)
    if not product.user_id == user.id:
        raise ValueError("Not your product")
    stripe.Product.delete(product.product_stripe_id)
    product.delete()
    return HttpResponseRedirect(reverse("home"))
