from django.shortcuts import render, redirect
from django.contrib import messages
from django import forms
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.models import User
from .forms import (
    RegisterUserForm,
    LoginUserForm,
)
import stripe
from niki_shop.settings import STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY


def get_session_user(request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise ValueError("You are not logged or don't have permission")
    else:
        user = User.objects.get(pk=user_id)
        return user


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
    return render(request, "shop/home.html", {"user": user})


def register_in_stripe(request):
    user = get_session_user(request)
    try:
        stripe.api_key = STRIPE_SECRET_KEY
        user_stripe_account = stripe.Account.create(
            type="standard",
            country="BG",
            email=user.email,

        )
        messages.success(request, "user_stripe_account")
    except Exception as e:
        messages.success(request, e)
        return redirect("home")
    return render(request, "shop/home.html", {"user": user, "stripe": user_stripe_account})
