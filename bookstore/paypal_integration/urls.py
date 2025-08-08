# paypal_integration/urls.py
from django.urls import path
from . import views

app_name = 'paypal_integration'

urlpatterns = [
    path('create/<str:order_id>/', views.create_payment, name='create_payment'),
    path('execute/<str:order_id>/', views.execute_payment, name='execute_payment'),
    path('cancelled/<str:order_id>/', views.payment_cancelled, name='payment_cancelled'),
    path('success/<str:order_id>/', views.payment_success, name='payment_success'),
]
