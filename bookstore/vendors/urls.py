# vendors/urls.py - Add these URLs to your existing patterns

from django.urls import path
from . import views

app_name = 'vendors'

urlpatterns = [
    # Existing URLs
    path('register/', views.vendor_register, name='register'),
    path('dashboard/', views.vendor_dashboard, name='dashboard'),
    path('offers/', views.stock_offers_list, name='stock_offers'),
    path('submit-offer/', views.submit_stock_offer, name='submit_offer'),
    path('tickets/', views.vendor_tickets, name='tickets'),
    path('create-ticket/', views.create_ticket, name='create_ticket'),
    path('ticket/<str:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('notifications/', views.vendor_notifications, name='notifications'),
    

    # DELIVERY MANAGEMENT URLS - FIXED ORDER
    path('offers-awaiting-delivery/', views.offers_awaiting_delivery, name='offers_awaiting_delivery'),
    
    # FIXED: Bulk scheduling BEFORE single scheduling to avoid conflicts
    path('bulk-schedule-delivery/', views.bulk_schedule_delivery, name='bulk_schedule_delivery'),
    path('schedule-delivery/bulk/', views.bulk_schedule_delivery, name='bulk_schedule_delivery'),
    path('schedule-delivery/<int:offer_id>/', views.schedule_delivery, name='schedule_delivery'),    
    path('track-delivery/<int:offer_id>/', views.track_delivery, name='track_delivery'),
    path('delivery-history/', views.delivery_history, name='delivery_history'),
    

    # API endpoints
    path('api/books/', views.book_search_api, name='book_search_api'),
    path('api/categories/', views.categories_api, name='categories_api'),
    path('api/category-books/', views.category_books_api, name='category_books_api'),
    path('api/notifications/count/', views.notifications_count, name='notifications_count'),
    path('submit-multiple-offer/', views.submit_multiple_offer, name='submit_multiple_offer'),
    path('submit-category-bulk-offer/', views.submit_category_bulk_offer, name='submit_category_bulk_offer'),
]