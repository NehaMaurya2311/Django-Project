# orders/admin.py
from django.contrib import admin
from .models import Order, OrderItem, OrderTracking, Return, ReturnItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['total']

class OrderTrackingInline(admin.TabularInline):
    model = OrderTracking
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'user', 'status', 'payment_status', 'total_amount', 'created_at']
    list_filter = ['status', 'payment_status', 'created_at']
    search_fields = ['order_id', 'user__username', 'billing_email']
    readonly_fields = ['order_id', 'created_at', 'updated_at']
    inlines = [OrderItemInline, OrderTrackingInline]

@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = ['return_id', 'order', 'reason', 'status', 'refund_amount', 'requested_at']
    list_filter = ['status', 'reason', 'requested_at']
    search_fields = ['return_id', 'order__order_id']

admin.site.register(OrderItem)
admin.site.register(OrderTracking)
admin.site.register(ReturnItem)
