# delivery/urls.py
from django.urls import path
from . import views

app_name = 'delivery'

urlpatterns = [
    path('track/<str:order_id>/', views.track_delivery, name='track_delivery'),
    path('dashboard/', views.delivery_dashboard, name='dashboard'),
]