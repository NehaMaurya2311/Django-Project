# books/urls.py - Updated URLs for three-level category hierarchy

from django.urls import path
from . import views

app_name = 'books'

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    
    # Book management
    path('books/', views.all_books, name='all_books'),
    path('book/<slug:slug>/', views.book_detail, name='book_detail'),
    path('add-book/', views.add_book, name='add_book'),
    path('delete-book/<slug:slug>/', views.delete_book, name='delete_book'),
    
    # Search
    path('search/', views.search_books, name='search_books'),
    path('search-google-books/', views.search_google_books, name='search_google_books'),
    
    # Category hierarchy URLs
    path('category/<slug:slug>/', views.category_books, name='category_books'),
    path('category/<slug:category_slug>/<slug:subcategory_slug>/', views.subcategory_books, name='subcategory_books'),
    path('category/<slug:category_slug>/<slug:subcategory_slug>/<slug:subsubcategory_slug>/', views.subsubcategory_books, name='subsubcategory_books'),
    
    # Cart management
    path('cart/', views.cart_view, name='cart'),
    path('add-to-cart/<int:book_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart-item/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    
    # AJAX endpoints
    path('ajax/load-subcategories/', views.load_subcategories, name='load_subcategories'),
    path('ajax/load-subsubcategories/', views.load_subsubcategories, name='load_subsubcategories'),
    path('ajax/check-book-exists/', views.check_book_exists, name='check_book_exists'),
]