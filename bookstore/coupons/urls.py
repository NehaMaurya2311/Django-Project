# coupons/urls.py
from django.urls import path
from . import views

app_name = 'coupons'

urlpatterns = [
    path('validate/', views.validate_coupon, name='validate_coupon'),
    path('available/', views.available_coupons, name='available_coupons'),
]