# vendors/urls.py
from django.urls import path
from . import views

app_name = 'vendors'

urlpatterns = [
    path('register/', views.vendor_register, name='register'),
    path('dashboard/', views.vendor_dashboard, name='dashboard'),
    path('offers/', views.stock_offers_list, name='stock_offers'),
    path('offers/submit/', views.submit_stock_offer, name='submit_offer'),
    path('tickets/', views.vendor_tickets, name='tickets'),
    path('tickets/create/', views.create_ticket, name='create_ticket'),
    path('tickets/<str:ticket_id>/', views.ticket_detail, name='ticket_detail'),
]
