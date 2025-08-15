# warehouse/urls.py - ENHANCED with Stock Offer Management
from django.urls import path
from . import views

app_name = 'warehouse'

urlpatterns = [
    # Dashboard
    path('', views.warehouse_dashboard, name='dashboard'),
    
    # Stock Management
    path('stock/', views.stock_list, name='stock_list'),
    path('stock/<int:stock_id>/', views.stock_detail, name='stock_detail'),
    path('stock/<int:stock_id>/add/', views.add_stock, name='add_stock'),
    path('stock/<int:stock_id>/remove/', views.remove_stock, name='remove_stock'),
    path('stock/<int:stock_id>/location/', views.update_stock_location, name='update_location'),
    
    # Stock Offer Management - NEW ROUTES
    path('offers/', views.stock_offers_list, name='stock_offers_list'),
    path('offers/<int:offer_id>/', views.offer_detail, name='offer_detail'),
    path('offers/<int:offer_id>/approve/', views.approve_offer, name='approve_offer'),
    path('offers/<int:offer_id>/reject/', views.reject_offer, name='reject_offer'),
    
    # Vendor Management
    path('vendors/<int:vendor_id>/offers/', views.vendor_offers, name='vendor_offers'),
    
    # Reports
    path('reports/low-stock/', views.low_stock_report, name='low_stock_report'),
]