# warehouse/urls.py
from django.urls import path
from . import views

app_name = 'warehouse'

urlpatterns = [
    path('', views.warehouse_dashboard, name='dashboard'),
    path('stock/', views.stock_list, name='stock_list'),
    path('stock/<int:stock_id>/', views.stock_detail, name='stock_detail'),
    path('stock/<int:stock_id>/add/', views.add_stock, name='add_stock'),
    path('stock/<int:stock_id>/remove/', views.remove_stock, name='remove_stock'),
    path('reports/low-stock/', views.low_stock_report, name='low_stock_report'),
]