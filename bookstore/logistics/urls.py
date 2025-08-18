# logistics/urls.py - ENHANCED VERSION
from django.urls import path
from . import views

app_name = 'logistics'

urlpatterns = [
    # Dashboard
    path('', views.logistics_dashboard, name='dashboard'),

    path('partners/', views.logistics_partner_list, name='partner_list'),
    path('partners/create/', views.logistics_partner_create, name='partner_create'),
    path('partners/<int:partner_id>/edit/', views.logistics_partner_edit, name='partner_edit'),
    
    # NEW DELIVERY SCHEDULE MANAGEMENT
    path('deliveries/', views.delivery_list, name='delivery_list'),
    path('deliveries/<int:delivery_id>/', views.delivery_detail, name='delivery_detail'),
    path('deliveries/<int:delivery_id>/assign-partner/', views.assign_logistics_partner, name='assign_partner'),
    path('deliveries/<int:delivery_id>/update-status/', views.update_delivery_status, name='update_status'),
    
    # STOCK RECEIPT CONFIRMATION
    path('pending-receipts/', views.pending_receipts, name='pending_receipts'),
    path('deliveries/<int:delivery_id>/confirm-receipt/', views.confirm_stock_receipt, name='confirm_receipt'),
    
    # LEGACY PICKUP SYSTEM (for backward compatibility)
    path('pickups/', views.pickup_list, name='pickup_list'),
    path('pickups/<int:pickup_id>/', views.pickup_detail, name='pickup_detail'),
]