# wishlist/urls.py
from django.urls import path
from . import views

app_name = 'wishlist'

urlpatterns = [
    path('', views.wishlist, name='wishlist'),
    path('add/<int:book_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove/<int:book_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('move-to-cart/<int:book_id>/', views.move_to_cart, name='move_to_cart'),
    path('collections/', views.collections, name='collections'),
    path('collections/<int:collection_id>/', views.collection_detail, name='collection_detail'),
]