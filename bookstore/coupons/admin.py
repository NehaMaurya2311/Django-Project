# coupons/admin.py
from django.contrib import admin
from .models import Coupon, CouponUsage

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'discount_type', 'discount_value', 'valid_from', 'valid_to', 'is_active']
    list_filter = ['discount_type', 'is_active', 'valid_from', 'valid_to']
    search_fields = ['code', 'name']
    filter_horizontal = ['applicable_categories', 'applicable_books', 'excluded_users']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ['coupon', 'user', 'order', 'discount_amount', 'used_at']
    list_filter = ['used_at', 'coupon']
    search_fields = ['coupon__code', 'user__username', 'order__order_id']
