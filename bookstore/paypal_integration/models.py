# paypal_integration/models.py
from django.db import models
from django.contrib.auth import get_user_model
from orders.models import Order

User = get_user_model()

class PayPalPayment(models.Model):
    PAYMENT_STATUS = (
        ('created', 'Created'),
        ('approved', 'Approved'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    )
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='paypal_payment')
    paypal_payment_id = models.CharField(max_length=100, unique=True)
    paypal_payer_id = models.CharField(max_length=100, blank=True)
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='created')
    
    payment_method = models.CharField(max_length=50, default='paypal')
    
    approval_url = models.URLField(blank=True)
    execute_url = models.URLField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # PayPal response data
    paypal_response = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"PayPal Payment {self.paypal_payment_id} for Order {self.order.order_id}"
