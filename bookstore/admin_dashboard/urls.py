# admin_dashboard/urls.py
from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    # Main dashboard
    path('', views.dashboard_home, name='dashboard'),
    
    # Products management
    path('products/', views.products_list, name='products_list'),
    path('categories/', views.categories_list, name='categories_list'),
    path('categories/<slug:category_slug>/products/', views.category_products, name='category_products'),
    
    # Warehouse management
    path('warehouse/', views.warehouse_dashboard, name='warehouse_dashboard'),
    
    # Orders management
    path('orders/', views.orders_list, name='orders_list'),
    
    # Vendors management
    path('vendors/', views.vendors_list, name='vendors_list'),
    
    # Coupons management
    path('coupons/', views.coupons_list, name='coupons_list'),
    
    # API endpoints for charts
    path('api/data/', views.dashboard_api_data, name='api_data'),
]

# Add this to your main urls.py:
# path('admin-dashboard/', include('admin_dashboard.urls')),