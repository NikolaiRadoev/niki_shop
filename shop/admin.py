from django.contrib import admin
from .models import StripeData, Product, BuyProducts

# Register your models here.
admin.site.register(StripeData)
admin.site.register(Product)
admin.site.register(BuyProducts)

