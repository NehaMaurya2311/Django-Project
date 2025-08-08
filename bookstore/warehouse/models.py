# warehouse/models.py
from django.db import models
from django.contrib.auth import get_user_model
from books.models import Book, Category, SubCategory
from vendors.models import VendorProfile

User = get_user_model()

class Stock(models.Model):
    book = models.OneToOneField(Book, on_delete=models.CASCADE, related_name='stock')
    quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10, help_text="Minimum stock level before reorder")
    max_stock_level = models.PositiveIntegerField(default=100)
    
    location_shelf = models.CharField(max_length=20, blank=True, help_text="Shelf location in warehouse")
    location_row = models.CharField(max_length=10, blank=True)
    location_section = models.CharField(max_length=10, blank=True)
    
    reserved_quantity = models.PositiveIntegerField(default=0, help_text="Quantity reserved for orders")
    
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['book__title']
    
    def __str__(self):
        return f"{self.book.title} - Stock: {self.available_quantity}"
    
    @property
    def available_quantity(self):
        return self.quantity - self.reserved_quantity
    
    @property
    def needs_reorder(self):
        return self.available_quantity <= self.reorder_level
    
    @property
    def is_out_of_stock(self):
        return self.available_quantity <= 0
    
    def get_location(self):
        if self.location_section and self.location_row and self.location_shelf:
            return f"{self.location_section}-{self.location_row}-{self.location_shelf}"
        return "Not Assigned"

class StockMovement(models.Model):
    MOVEMENT_TYPES = (
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('adjustment', 'Stock Adjustment'),
        ('damaged', 'Damaged'),
        ('returned', 'Customer Return'),
        ('transfer', 'Internal Transfer'),
    )
    
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='movements')
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField(help_text="Positive for IN, Negative for OUT")
    reference = models.CharField(max_length=100, help_text="Order ID, Vendor ID, etc.")
    reason = models.CharField(max_length=200, blank=True)
    
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.stock.book.title} - {self.movement_type} ({self.quantity})"
    
    def save(self, *args, **kwargs):
        # Update stock quantity
        if self.pk is None:  # New movement
            if self.movement_type in ['in', 'returned', 'adjustment'] and self.quantity > 0:
                self.stock.quantity += abs(self.quantity)
            elif self.movement_type in ['out', 'damaged'] and self.quantity < 0:
                self.stock.quantity += self.quantity  # Subtract (quantity is negative)
            
            self.stock.save()
        
        super().save(*args, **kwargs)

class CategoryStock(models.Model):
    category = models.OneToOneField(Category, on_delete=models.CASCADE, related_name='category_stock')
    total_books = models.PositiveIntegerField(default=0)
    total_quantity = models.PositiveIntegerField(default=0)
    out_of_stock_books = models.PositiveIntegerField(default=0)
    low_stock_books = models.PositiveIntegerField(default=0)
    
    last_updated = models.DateTimeField(auto_now=True)
    
    def update_stats(self):
        from django.db.models import Count, Sum, Q
        
        stocks = Stock.objects.filter(book__category=self.category)
        
        self.total_books = stocks.count()
        self.total_quantity = stocks.aggregate(Sum('quantity'))['quantity__sum'] or 0
        self.out_of_stock_books = stocks.filter(quantity=0).count()
        self.low_stock_books = stocks.filter(
            Q(quantity__lte=models.F('reorder_level')) & Q(quantity__gt=0)
        ).count()
        
        self.save()
    
    def __str__(self):
        return f"{self.category.name} Stock Summary"

class InventoryAudit(models.Model):
    AUDIT_STATUS = (
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    audit_id = models.CharField(max_length=20, unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, null=True, blank=True)
    
    scheduled_date = models.DateField()
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=AUDIT_STATUS, default='scheduled')
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Audit #{self.audit_id} - {self.status}"
    
    def save(self, *args, **kwargs):
        if not self.audit_id:
            import uuid
            self.audit_id = f"IA{str(uuid.uuid4())[:8].upper()}"
        super().save(*args, **kwargs)

class InventoryAuditItem(models.Model):
    audit = models.ForeignKey(InventoryAudit, on_delete=models.CASCADE, related_name='items')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    
    system_quantity = models.PositiveIntegerField()
    actual_quantity = models.PositiveIntegerField()
    variance = models.IntegerField(default=0)
    
    notes = models.CharField(max_length=200, blank=True)
    
    def save(self, *args, **kwargs):
        self.variance = self.actual_quantity - self.system_quantity
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.audit.audit_id} - {self.stock.book.title}"
