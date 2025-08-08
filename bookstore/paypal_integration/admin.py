# paypal_integration/admin.py
from django.contrib import admin
from .models import PayPalPayment

@admin.register(PayPalPayment)
class PayPalPaymentAdmin(admin.ModelAdmin):
    list_display = ['order', 'paypal_payment_id', 'amount', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['order__order_id', 'paypal_payment_id']
    readonly_fields = ['created_at', 'updated_at', 'completed_at']