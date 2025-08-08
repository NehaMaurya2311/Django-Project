from django.db import models
from django.contrib.auth import get_user_model
from orders.models import Order

User = get_user_model()

class DeliveryPartner(models.Model):
    PARTNER_STATUS = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    )
    
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    address = models.TextField()
    
    service_areas = models.JSONField(default=list, help_text="List of pincodes they serve")
    
    status = models.CharField(max_length=20, choices=PARTNER_STATUS, default='active')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    
    cost_per_delivery = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def serves_pincode(self, pincode):
        return pincode in self.service_areas

class Delivery(models.Model):
    DELIVERY_STATUS = (
        ('assigned', 'Assigned'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('failed', 'Delivery Failed'),
        ('returned', 'Returned to Sender'),
    )
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='delivery')
    delivery_partner = models.ForeignKey(DeliveryPartner, on_delete=models.SET_NULL, null=True, related_name='deliveries')
    
    pickup_address = models.TextField(help_text="Warehouse or pickup location")
    delivery_address = models.TextField()
    
    assigned_at = models.DateTimeField(auto_now_add=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    estimated_delivery_time = models.DateTimeField()
    actual_delivery_time = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=DELIVERY_STATUS, default='assigned')
    
    tracking_id = models.CharField(max_length=50, blank=True)
    delivery_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    
    delivery_notes = models.TextField(blank=True)
    customer_rating = models.PositiveIntegerField(null=True, blank=True, help_text="1-5 rating")
    customer_feedback = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Delivery for Order #{self.order.order_id}"
    
    def save(self, *args, **kwargs):
        if not self.tracking_id:
            import uuid
            self.tracking_id = f"TRK{str(uuid.uuid4())[:10].upper()}"
        super().save(*args, **kwargs)

class DeliveryUpdate(models.Model):
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name='updates')
    status = models.CharField(max_length=20, choices=Delivery.DELIVERY_STATUS)
    location = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.delivery.tracking_id} - {self.status}"

class DeliveryLocation(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    is_warehouse = models.BooleanField(default=False)
    is_pickup_point = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.name} - {self.city}"
