# books/urls.py
from django.urls import path
from . import views

app_name = 'books'

urlpatterns = [
    path('', views.home, name='home'),
    path('book/<slug:slug>/', views.book_detail, name='book_detail'),
    path('category/<slug:slug>/', views.category_books, name='category_books'),
    path('category/<slug:category_slug>/<slug:subcategory_slug>/', views.subcategory_books, name='subcategory'),
    path('books/', views.all_books, name='all_books'),
    path('search/', views.search_books, name='search'),
    
    # Book management URLs
    path('add-book/', views.add_book, name='add_book'),
    path('search-google-books/', views.search_google_books, name='search_google_books'),
    path('delete-book/<slug:slug>/', views.delete_book, name='delete_book'),
    
    # Cart URLs
    path('cart/', views.cart_view, name='cart'),
    path('add-to-cart/<int:book_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart-item/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('remove-from-cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
]