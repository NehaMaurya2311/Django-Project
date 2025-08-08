# logistics/urls.py
from django.urls import path
from . import views

app_name = 'logistics'

urlpatterns = [
    path('', views.logistics_dashboard, name='dashboard'),
    path('pickups/', views.pickup_list, name='pickup_list'),
    path('pickups/<int:pickup_id>/', views.pickup_detail, name='pickup_detail'),
]
