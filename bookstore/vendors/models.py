# vendors/models.py
from django.db import models
from django.contrib.auth import get_user_model
from books.models import Book

User = get_user_model()

class VendorProfile(models.Model):
    VENDOR_STATUS = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('suspended', 'Suspended'),
        ('rejected', 'Rejected'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor_profile')
    business_name = models.CharField(max_length=200)
    business_registration_number = models.CharField(max_length=100, blank=True)
    contact_person = models.CharField(max_length=100)
    business_address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    website = models.URLField(blank=True)
    
    business_license = models.FileField(upload_to='vendor_documents/', blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    
    bank_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    ifsc_code = models.CharField(max_length=20, blank=True)
    
    status = models.CharField(max_length=20, choices=VENDOR_STATUS, default='pending')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.business_name

class StockOffer(models.Model):
    OFFER_STATUS = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processed', 'Processed'),
    )
    
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='stock_offers')
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    availability_date = models.DateField()
    expiry_date = models.DateField(help_text="Until when this offer is valid")
    
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=OFFER_STATUS, default='pending')
    
    admin_notes = models.TextField(blank=True, help_text="Admin's notes on this offer")
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_offers')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Add delivery scheduling fields
    vendor_delivery_date = models.DateTimeField(null=True, blank=True, 
        help_text="When vendor will deliver the books")
    vendor_contact_person = models.CharField(max_length=100, blank=True)
    vendor_contact_phone = models.CharField(max_length=15, blank=True)
    
    # Tracking fields
    is_delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    delivered_quantity = models.PositiveIntegerField(null=True, blank=True)
    staff_confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    staff_confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.vendor.business_name} - {self.book.title} ({self.quantity} units)"
    
    def save(self, *args, **kwargs):
        self.total_amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)

class VendorTicket(models.Model):
    TICKET_STATUS = (
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )
    
    TICKET_PRIORITY = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    TICKET_CATEGORY = (
        ('logistics', 'Logistics Issue'),
        ('payment', 'Payment Issue'),
        ('quality', 'Quality Concern'),
        ('delivery', 'Delivery Issue'),
        ('general', 'General Inquiry'),
        ('technical', 'Technical Support'),
    )
    
    vendor = models.ForeignKey(VendorProfile, on_delete=models.CASCADE, related_name='tickets')
    ticket_id = models.CharField(max_length=20, unique=True)
    subject = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=TICKET_CATEGORY, default='general')
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=TICKET_PRIORITY, default='medium')
    status = models.CharField(max_length=20, choices=TICKET_STATUS, default='open')
    
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_vendor_tickets')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"#{self.ticket_id} - {self.subject}"
    
    def save(self, *args, **kwargs):
        if not self.ticket_id:
            import uuid
            self.ticket_id = f"VT{str(uuid.uuid4())[:8].upper()}"
        super().save(*args, **kwargs)

class VendorTicketResponse(models.Model):
    ticket = models.ForeignKey(VendorTicket, on_delete=models.CASCADE, related_name='responses')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    response = models.TextField()
    is_internal = models.BooleanField(default=False, help_text="Internal notes, not visible to vendor")
    attachment = models.FileField(upload_to='ticket_attachments/', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Response to {self.ticket.ticket_id} by {self.user.username}"


class OfferStatusNotification(models.Model):
    stock_offer = models.ForeignKey(StockOffer, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=[
        ('approved', 'Offer Approved - Schedule Delivery'),
        ('pickup_scheduled', 'Pickup Scheduled'),
        ('in_transit', 'Books in Transit'),
        ('delivered', 'Delivered to Warehouse'),
        ('confirmed', 'Stock Confirmed & Added'),
    ])
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)