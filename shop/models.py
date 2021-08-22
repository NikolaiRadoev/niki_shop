from django.db import models
from django.contrib.auth.models import User


# Create your models here.
class StripeData(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stripe_id = models.CharField(max_length=200)
