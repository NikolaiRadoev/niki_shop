from django.urls import path
from . import views


urlpatterns = [
    path("", views.index, name="index"),
    path("register/", views.register, name="register"),
    path("login/", views.login, name="login"),
    path("home/", views.home, name="home"),
    path("logout/", views.logout, name="logout"),
    path("create_stripe_account/", views.register_in_stripe, name="register_in_stripe"),
    path("create/new/product/", views.create_product, name="create_product"),
    path("edit/product/<int:product_id>/", views.edit_product, name="edit_product"),
    path("detail/product/<int:product_id>/", views.detail_product, name="detail_product"),
    path("delete/product/<int:product_id>/", views.delete_product, name="delete_product"),
]