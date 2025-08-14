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
    path('api/search-books/', views.book_search_api, name='book_search_api'),
    path('api/category-books/', views.category_books_api, name='category_books_api'),
    path('api/categories/', views.categories_api, name='categories_api'),
    
    # Enhanced offer submission
    path('submit-offer/multiple/', views.submit_multiple_offer, name='submit_multiple_offer'),
    path('submit-offer/category-bulk/', views.submit_category_bulk_offer, name='submit_category_bulk_offer'),
]


