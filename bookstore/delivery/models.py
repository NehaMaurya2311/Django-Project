# delivery/models.py
from django.db import models
from django.contrib.auth import get_user_model
from orders.models import Order
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import datetime, timedelta

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
    
    # Capacity management
    max_daily_deliveries = models.PositiveIntegerField(default=50)
    current_load = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def serves_pincode(self, pincode):
        return pincode in self.service_areas
    
    def can_take_delivery(self):
        """Check if partner can take more deliveries today"""
        from datetime import date
        today_deliveries = self.deliveries.filter(
            assigned_at__date=date.today(),
            status__in=['assigned', 'picked_up', 'in_transit', 'out_for_delivery']
        ).count()
        return today_deliveries < self.max_daily_deliveries
    
    @classmethod
    def get_default_partner(cls, pincode=None):
        """Get default partner for auto-assignment"""
        # Try to find a partner that serves the pincode and has capacity
        if pincode:
            partners = cls.objects.filter(
                status='active',
                service_areas__contains=[pincode]
            )
            for partner in partners:
                if partner.can_take_delivery():
                    return partner
        
        # Fallback: get any active partner with capacity
        partners = cls.objects.filter(status='active')
        for partner in partners:
            if partner.can_take_delivery():
                return partner
        
        # If no partners available, return None (will be manually assigned)
        return None

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
    delivery_partner = models.ForeignKey(
        DeliveryPartner, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='deliveries'
    )
    
    pickup_address = models.TextField(help_text="Warehouse or pickup location")
    delivery_address = models.TextField()
    
    assigned_at = models.DateTimeField(auto_now_add=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    estimated_delivery_time = models.DateTimeField()
    actual_delivery_time = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=DELIVERY_STATUS, default='assigned')
    
    tracking_id = models.CharField(max_length=50, blank=True, unique=True)
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

# Signal to automatically create delivery when order is confirmed
@receiver(post_save, sender=Order)
def create_delivery_for_order(sender, instance, created, **kwargs):
    """
    Automatically create delivery when order status changes to 'confirmed'
    """
    if instance.status == 'confirmed' and not hasattr(instance, 'delivery'):
        # Get default warehouse address (you may need to adjust this)
        try:
            warehouse = DeliveryLocation.objects.filter(is_warehouse=True).first()
            if warehouse:
                pickup_address = f"{warehouse.address}, {warehouse.city}, {warehouse.state} - {warehouse.pincode}"
            else:
                pickup_address = "Main Warehouse, BookStore HQ, Mumbai, Maharashtra - 400001"  # Default
        except:
            pickup_address = "Main Warehouse, BookStore HQ, Mumbai, Maharashtra - 400001"
        
        # Create delivery address from order shipping info
        delivery_address = f"{instance.shipping_address}, {instance.shipping_city}, {instance.shipping_state} - {instance.shipping_pincode}"
        
        # Calculate estimated delivery time (3-5 business days)
        estimated_delivery = datetime.now() + timedelta(days=4)
        
        # Try to get a delivery partner
        delivery_partner = DeliveryPartner.get_default_partner(instance.shipping_pincode)
        
        # Calculate delivery cost (you can make this more sophisticated)
        delivery_cost = 50.00  # Default delivery cost
        if delivery_partner:
            delivery_cost = float(delivery_partner.cost_per_delivery) if delivery_partner.cost_per_delivery > 0 else 50.00
        
        # Create the delivery
        delivery = Delivery.objects.create(
            order=instance,
            delivery_partner=delivery_partner,
            pickup_address=pickup_address,
            delivery_address=delivery_address,
            estimated_delivery_time=estimated_delivery,
            delivery_cost=delivery_cost,
            status='assigned'
        )
        
        # Create initial delivery update
        DeliveryUpdate.objects.create(
            delivery=delivery,
            status='assigned',
            description=f"Delivery assigned{'to ' + delivery_partner.name if delivery_partner else ' - awaiting partner assignment'}. Estimated delivery: {estimated_delivery.strftime('%B %d, %Y')}"
        )
        
        print(f"✅ Delivery created for Order #{instance.order_id} with tracking ID: {delivery.tracking_id}")

# Signal to update delivery status when order status changes
@receiver(post_save, sender=Order)
def update_delivery_status(sender, instance, **kwargs):
    """
    Update delivery status based on order status changes
    """
    if hasattr(instance, 'delivery'):
        delivery = instance.delivery
        
        # Map order status to delivery status
        status_mapping = {
            'confirmed': 'assigned',
            'processing': 'assigned',
            'shipped': 'picked_up',
            'delivered': 'delivered',
            'cancelled': 'returned',  # If order is cancelled, mark delivery as returned
        }
        
        if instance.status in status_mapping:
            new_delivery_status = status_mapping[instance.status]
            
            if delivery.status != new_delivery_status:
                old_status = delivery.status
                delivery.status = new_delivery_status
                
                # Set timestamps
                if new_delivery_status == 'picked_up' and not delivery.picked_up_at:
                    delivery.picked_up_at = datetime.now()
                elif new_delivery_status == 'delivered' and not delivery.delivered_at:
                    delivery.delivered_at = datetime.now()
                    delivery.actual_delivery_time = datetime.now()
                
                delivery.save()
                
                # Create delivery update
                DeliveryUpdate.objects.create(
                    delivery=delivery,
                    status=new_delivery_status,
                    description=f"Status updated from {old_status} to {new_delivery_status} based on order status change."
                )