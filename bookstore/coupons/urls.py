# coupons/urls.py
from django.urls import path
from . import views

app_name = 'coupons'

urlpatterns = [
    path('validate/', views.validate_coupon, name='validate_coupon'),
    path('available/', views.available_coupons, name='available_coupons'),
    path('sale-books/', views.sale_books, name='sale_books'),
    path('cart-coupons/', views.cart_coupons_ajax, name='cart_coupons_ajax'),
    path('book-sale-info/<int:book_id>/', views.get_book_sale_info, name='get_book_sale_info'),
]