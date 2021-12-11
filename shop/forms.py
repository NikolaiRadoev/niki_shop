import stripe

from django import forms
from django.db import transaction
from django.forms import ModelForm
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password
from niki_shop.settings import STRIPE_SECRET_KEY
from .models import Product, ProductPurchase

stripe.api_key = STRIPE_SECRET_KEY


class RegisterUserForm(ModelForm):
    class Meta:
        model = User
        fields = ["username", "email", "password", "first_name", "last_name"]
        labels = {"email": "Email"}
        widgets = {
            "password": forms.PasswordInput(),
            "email": forms.EmailInput(),
        }

    def clean(self):
        cleaned_data = super(RegisterUserForm, self).clean()
        user_email_input = cleaned_data["email"]

        try:
            User.objects.get(email=user_email_input)
            raise forms.ValidationError("email is taken")
        except User.DoesNotExist:
            return cleaned_data

    def save(self, request):
        username_input = self.cleaned_data["username"]
        password_input = self.cleaned_data["password"]
        user_email_input = self.cleaned_data["email"]
        first_name_input = self.cleaned_data["first_name"]
        last_name_input = self.cleaned_data["last_name"]

        hash_password = make_password(password_input)

        user = User(
            username=username_input,
            password=hash_password,
            email=user_email_input,
            first_name=first_name_input,
            last_name=last_name_input,
        )
        user.save()
        request.session["user_id"] = user.id


class LoginUserForm(ModelForm):
    class Meta:
        model = User
        fields = ["email", "password"]
        labels = {"email": "Email"}
        widgets = {
            "password": forms.PasswordInput(),
            "email": forms.EmailInput(),
        }

    def clean(self):
        cleaned_data = super(LoginUserForm, self).clean()
        try:
            password = cleaned_data["password"]
            user = User.objects.get(email=cleaned_data["email"])
            if check_password(password, user.password):
                cleaned_data["user"] = user
            else:
                raise forms.ValidationError("Wrong email or password")
        except User.DoesNotExist:
            raise forms.ValidationError("Wrong email or password")
        return cleaned_data

    def save(self, request):
        user = self.cleaned_data["user"]
        request.session["user_id"] = user.id


class ProductForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = kwargs.pop("user")
        if not getattr(self.instance, "user", None):
            self.instance.user = self.user

    class Meta:
        model = Product
        fields = ["name", "description", "price", "currency", "total_quantity"]
        labels = {"total_quantity": "Quantity"}
        widgets = {
            "description": forms.Textarea(),
            "currency": forms.Select(
                choices=[("BGN", "BGN"), ("USD", "USD"), ("EUR", "EUR")]
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        if not self.user.id == self.instance.user.id:
            raise forms.ValidationError("Not your product")
        return cleaned_data


class BuyProductsForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.product = kwargs.pop("product")
        super().__init__(*args, **kwargs)

    class Meta:
        model = Product
        fields = ["total_quantity"]
        labels = {"total_quantity": "Quantity"}

    def clean(self):
        cleaned_data = super(BuyProductsForm, self).clean()
        if cleaned_data["total_quantity"] <= 0:
            raise ValueError("Quantity can't be 0 or less")
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        purchase = ProductPurchase(
            buyer=self.user,
            product=self.product,
            product_name=self.product.name,
            product_price=self.product.price,
            product_currency=self.product.currency,
            quantity=self.cleaned_data["total_quantity"],
        )
        purchase.save()
        self.product.total_quantity -= purchase.quantity
        self.product.save()
