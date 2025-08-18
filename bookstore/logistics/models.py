# logistics/models.py
from django.db import models
from django.contrib.auth import get_user_model
from vendors.models import VendorProfile, StockOffer
from warehouse.models import Stock

User = get_user_model()

class LogisticsPartner(models.Model):
    PARTNER_STATUS = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    )
    
    VEHICLE_TYPES = (
        ('bike', 'Bike'),
        ('car', 'Car'),
        ('van', 'Van'),
        ('truck', 'Truck'),
    )
    
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    vehicle_number = models.CharField(max_length=20)
    driver_license = models.CharField(max_length=50, blank=True)
    
    service_areas = models.JSONField(default=list, help_text="List of cities/areas they serve")
    status = models.CharField(max_length=20, choices=PARTNER_STATUS, default='active')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    
    cost_per_km = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    base_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} - {self.vehicle_type}"

class VendorPickup(models.Model):
    PICKUP_STATUS = (
        ('scheduled', 'Scheduled'),
        ('assigned', 'Assigned to Partner'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered to Warehouse'),
        ('failed', 'Pickup Failed'),
        ('cancelled', 'Cancelled'),
    )
    
    stock_offer = models.OneToOneField(StockOffer, on_delete=models.CASCADE, related_name='pickup')
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='pickups')
    logistics_partner = models.ForeignKey(LogisticsPartner, on_delete=models.SET_NULL, null=True, blank=True, related_name='pickups')
    
    pickup_address = models.TextField()
    warehouse_address = models.TextField()
    
    scheduled_date = models.DateTimeField()
    pickup_date = models.DateTimeField(null=True, blank=True)
    delivery_date = models.DateTimeField(null=True, blank=True)
    
    estimated_distance = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Distance in KM")
    actual_distance = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    transport_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    status = models.CharField(max_length=20, choices=PICKUP_STATUS, default='scheduled')
    
    pickup_notes = models.TextField(blank=True)
    delivery_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Pickup for {self.stock_offer}"

class PickupTracking(models.Model):
    pickup = models.ForeignKey(VendorPickup, on_delete=models.CASCADE, related_name='tracking_updates')
    status = models.CharField(max_length=20, choices=VendorPickup.PICKUP_STATUS)
    location = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Pickup #{self.pickup.id} - {self.status}"

class VendorLocation(models.Model):
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='locations')
    name = models.CharField(max_length=100, help_text="Location name/identifier")
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    def __str__(self):
        return f"{self.vendor.business_name} - {self.name}"


# logistics/models.py - Enhanced tracking

class DeliverySchedule(models.Model):
    DELIVERY_STATUS = (
        ('scheduled', 'Scheduled by Vendor'),
        ('confirmed', 'Confirmed by Logistics'),
        ('pickup_assigned', 'Pickup Partner Assigned'),
        ('collected', 'Collected from Vendor'),
        ('in_transit', 'In Transit to Warehouse'),
        ('arrived', 'Arrived at Warehouse'),
        ('verified', 'Stock Verified by Staff'),
        ('completed', 'Stock Added to Inventory'),
    )
    
    stock_offer = models.OneToOneField(StockOffer, on_delete=models.CASCADE)
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE)
    
    # Vendor provided details
    scheduled_delivery_date = models.DateTimeField()
    vendor_location = models.ForeignKey(VendorLocation, on_delete=models.CASCADE)
    contact_person = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=15)
    special_instructions = models.TextField(blank=True)
    
    # Logistics details
    assigned_partner = models.ForeignKey(LogisticsPartner, on_delete=models.SET_NULL, null=True)
    estimated_pickup_time = models.DateTimeField(null=True, blank=True)
    actual_pickup_time = models.DateTimeField(null=True, blank=True)
    estimated_delivery_time = models.DateTimeField(null=True, blank=True)
    actual_delivery_time = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    
    # Stock verification
    delivered_quantity = models.PositiveIntegerField(null=True, blank=True)
    verified_quantity = models.PositiveIntegerField(null=True, blank=True)
    quality_notes = models.TextField(blank=True)
    
    status = models.CharField(max_length=20, choices=DELIVERY_STATUS, default='scheduled')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class DeliveryTracking(models.Model):
    """Track delivery status updates"""
    delivery = models.ForeignKey(
        'DeliverySchedule', 
        on_delete=models.CASCADE,
        related_name='tracking_updates'
    )
    status = models.CharField(
        max_length=20,
        choices=DeliverySchedule.DELIVERY_STATUS  # Reference from DeliverySchedule
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    location = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='delivery_updates',
        default=1
    )
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Delivery Tracking Update"
        verbose_name_plural = "Delivery Tracking Updates"
    
    def __str__(self):
        return f"Delivery #{self.delivery.id} - {self.get_status_display()} at {self.timestamp}"



class StockReceiptConfirmation(models.Model):
    delivery_schedule = models.OneToOneField(DeliverySchedule, on_delete=models.CASCADE)
    received_by_staff = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Verification details
    books_received = models.PositiveIntegerField()
    books_accepted = models.PositiveIntegerField()
    books_rejected = models.PositiveIntegerField(default=0)
    rejection_reason = models.TextField(blank=True)
    
    # Quality assessment
    condition_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], default=5)
    quality_notes = models.TextField(blank=True)
    
    # Stock update confirmation
    stock_updated = models.BooleanField(default=False)
    stock_movement_created = models.BooleanField(default=False)
    
    confirmed_at = models.DateTimeField(auto_now_add=True)