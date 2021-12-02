from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class StripeData(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stripe_id = models.CharField(max_length=200)


class Product(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product_stripe_id = models.CharField(max_length=200, null=True)
    price_stripe_id = models.CharField(max_length=200, null=True)
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=2000)
    price = models.FloatField(default=0)
    currency = models.CharField(max_length=200)
    total_quantity = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class BuyProducts(models.Model):
    user = models.ManyToManyField(User)
    product = models.ManyToManyField(Product)
    product_price = models.FloatField(default=0)
    product_currency = models.CharField(max_length=200)
    quantity = models.IntegerField(default=0)
    product_name = models.CharField(max_length=200, null=True)
    product_id = models.IntegerField(default=0, null=True)
