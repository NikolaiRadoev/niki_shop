from django import forms
from django.db import transaction
from django.utils.translation import gettext_lazy
from django.forms import ModelForm
from django.forms import formset_factory, inlineformset_factory
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import make_password, check_password
from .models import Product, BuyProducts
from django.shortcuts import render, redirect, get_object_or_404
import stripe
from niki_shop.settings import STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY

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


class CreateNewProduct(ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

    class Meta:
        model = Product
        fields = ["name", "description", "price", "currency", "total_quantity"]
        labels = {"total_quantity": "Quantity"}
        widgets = {
            "description": forms.Textarea(),
            "currency": forms.Select(choices=[('BGN', 'BGN'), ('USD', 'USD'), ('EUR', 'EUR')])
        }

    def clean(self):
        cleaned_data = super(CreateNewProduct, self).clean()
        return cleaned_data

    def save(self, commit=True):
        """stripe_product = stripe.Product.create(name=self.cleaned_data["name"],
                                               description=self.cleaned_data["description"],
                                               metadata={'price': str(self.cleaned_data["price"]),
                                                         'currency': str(self.cleaned_data["currency"]),
                                                         'total_quantity': str(self.cleaned_data["total_quantity"])})
        stripe.Price.create(unit_amount=int(self.cleaned_data["price"]) * 100,
                            currency=self.cleaned_data["currency"],
                            product=stripe_product.id)"""

        product = Product(
            user=self.user,
            # product_stripe_id=stripe_product.id,
            name=self.cleaned_data["name"],
            description=self.cleaned_data["description"],
            price=self.cleaned_data["price"],
            currency=self.cleaned_data["currency"],
            total_quantity=self.cleaned_data["total_quantity"],
        )
        product.save()


class EditProductForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.product_id = kwargs.pop("product_id")
        self.product = get_object_or_404(Product, id=self.product_id)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Product
        fields = ["name", "description", "price", "currency", "total_quantity"]
        labels = {"total_quantity": "Quantity"}
        widgets = {
            "description": forms.Textarea(),
            "currency": forms.Select(choices=[('BGN', 'BGN'), ('USD', 'USD'), ('EUR', 'EUR')])
        }

    def clean(self):
        cleaned_data = super(EditProductForm, self).clean()
        return cleaned_data

    def save(self, commit=True):
        """stripe.Product.modify(
            self.product.product_stripe_id,
            name=self.cleaned_data["name"],
            description=self.cleaned_data["description"],
            metadata={'price': str(self.cleaned_data["price"]),
                      'currency': str(self.cleaned_data["currency"]),
                      'total_quantity': str(self.cleaned_data["total_quantity"])}),

        stripe.Price.modify(
            self.product.product_stripe_id,
            unit_amount=int(self.cleaned_data["price"]) * 100,
            currency=self.cleaned_data["currency"],
        )"""

        self.product.name = self.cleaned_data["name"]
        self.product.description = self.cleaned_data["description"]
        self.product.price = self.cleaned_data["price"]
        self.product.currency = self.cleaned_data["currency"]
        self.product.total_quantity = self.cleaned_data["total_quantity"]
        self.product.save()


class BuyProductsForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.product = kwargs.pop("product")
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

    class Meta:
        model = Product
        fields = ["total_quantity"]
        labels = {"total_quantity": "Quantity"}

    def clean(self):
        cleaned_data = super(BuyProductsForm, self).clean()
        return cleaned_data

    def save(self, commit=True):
        buy_products = BuyProducts(
            # user=self.user,
            # product=self.product,
            product_price=self.product.price,
            product_currency=self.product.currency,
            quantity=self.cleaned_data["total_quantity"],
            product_name=self.product.name,
            product_id=self.product.id,
        )
        buy_products.save()
        buy_products.user.add(self.user)
        buy_products.product.add(self.product)

        self.product.total_quantity -= self.cleaned_data["total_quantity"]
        self.product.save()

