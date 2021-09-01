from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class StripeData(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stripe_id = models.CharField(max_length=200)


class Product(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=2000)
    price = models.FloatField(default=0)
    currency = models.CharField(max_length=200)
    total_quantity = models.IntegerField(default=0)

    def __str__(self):
        return self.name
