# wishlist/urls.py
from django.urls import path
from . import views

app_name = 'wishlist'

urlpatterns = [
    path('', views.wishlist, name='wishlist'),
    path('toggle/<int:book_id>/', views.toggle_wishlist, name='toggle'),
    path('add/<int:book_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove/<int:book_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('move-to-cart/<int:book_id>/', views.move_to_cart, name='move_to_cart'),
    
    # Collections URLs
    path('collections/', views.collections, name='collections'),
    path('collections/create/', views.create_collection, name='create_collection'),
    path('collections/<int:collection_id>/', views.collection_detail, name='collection_detail'),
    path('collections/<int:collection_id>/edit/', views.edit_collection, name='edit_collection'),
    path('collections/<int:collection_id>/delete/', views.delete_collection, name='delete_collection'),
    path('collections/<int:collection_id>/add-books/', views.add_books_to_collection, name='add_books_to_collection'),
    path('collections/<int:collection_id>/available-books/', views.get_available_books, name='get_available_books'),
    
    # Collection Item URLs
    path('collections/item/<int:item_id>/priority/', views.update_item_priority, name='update_item_priority'),
    path('collections/item/<int:item_id>/notes/', views.update_item_notes, name='update_item_notes'),
    path('collections/item/<int:item_id>/remove/', views.remove_from_collection, name='remove_from_collection'),
]