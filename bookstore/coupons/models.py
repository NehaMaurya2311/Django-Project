# coupons/models.py - Updated with Sales System
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from books.models import Category, Book
from decimal import Decimal
from django.utils import timezone

User = get_user_model()

class Coupon(models.Model):
    DISCOUNT_TYPES = (
        ('percentage', 'Percentage'),
        ('fixed_amount', 'Fixed Amount'),
        ('free_shipping', 'Free Shipping'),
    )
    
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100, help_text="Internal name for the coupon")
    description = models.TextField(blank=True)
    
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES, default='percentage')
    discount_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Usage limitations
    min_order_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        help_text="Minimum order amount to use this coupon"
    )
    max_discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Maximum discount amount for percentage coupons"
    )
    
    usage_limit = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Total number of times this coupon can be used"
    )
    usage_limit_per_user = models.PositiveIntegerField(
        default=1,
        help_text="Number of times each user can use this coupon"
    )
    
    # Validity
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    
    # Restrictions
    applicable_categories = models.ManyToManyField(
        Category, 
        blank=True,
        help_text="Leave empty to apply to all categories"
    )
    applicable_books = models.ManyToManyField(
        Book, 
        blank=True,
        help_text="Specific books this coupon applies to"
    )
    
    # User restrictions
    first_time_users_only = models.BooleanField(default=False)
    excluded_users = models.ManyToManyField(
        User, 
        blank=True,
        help_text="Users who cannot use this coupon"
    )
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def can_use(self, user, order_amount=0, cart_items=None):
        """Check if user can use this coupon"""
        current_time = timezone.now()
        
        # Basic checks
        if not self.is_active:
            return False, "Coupon is not active"
        
        if current_time < self.valid_from:
            return False, "Coupon is not yet valid"
        
        if current_time > self.valid_to:
            return False, "Coupon has expired"
        
        if order_amount < self.min_order_amount:
            return False, f"Minimum order amount is ₹{self.min_order_amount}"
        
        # Check usage limits
        total_usage = CouponUsage.objects.filter(coupon=self).count()
        if self.usage_limit and total_usage >= self.usage_limit:
            return False, "Coupon usage limit reached"
        
        user_usage = CouponUsage.objects.filter(coupon=self, user=user).count()
        if user_usage >= self.usage_limit_per_user:
            return False, "You have already used this coupon"
        
        # Check user restrictions
        if user in self.excluded_users.all():
            return False, "You are not eligible for this coupon"
        
        if self.first_time_users_only:
            from orders.models import Order
            if Order.objects.filter(user=user, payment_status='paid').exists():
                return False, "This coupon is for first-time users only"
        
        # Check if coupon applies to items in cart
        if cart_items:
            applicable_items = self.get_applicable_items(cart_items)
            if not applicable_items:
                return False, "This coupon doesn't apply to any items in your cart"
        
        return True, "Coupon is valid"
    
    def get_applicable_items(self, cart_items):
        """Get cart items that this coupon applies to"""
        applicable_items = []
        
        # If no specific restrictions, applies to all items
        if not self.applicable_categories.exists() and not self.applicable_books.exists():
            return cart_items
        
        for item in cart_items:
            book = item.book
            
            # Check if book is specifically included
            if self.applicable_books.filter(id=book.id).exists():
                applicable_items.append(item)
                continue
            
            # Check if book's category is included
            if self.applicable_categories.filter(id=book.category.id).exists():
                applicable_items.append(item)
                continue
        
        return applicable_items
    
    def calculate_discount(self, cart_items):
        """Calculate discount amount for applicable cart items"""
        applicable_items = self.get_applicable_items(cart_items)
        applicable_amount = sum(item.get_effective_price() * item.quantity for item in applicable_items)
        
        if self.discount_type == 'percentage':
            discount = (applicable_amount * self.discount_value) / 100
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
            return discount
        
        elif self.discount_type == 'fixed_amount':
            return min(self.discount_value, applicable_amount)
        
        elif self.discount_type == 'free_shipping':
            # This would be handled in shipping calculation
            return Decimal('0.00')
        
        return Decimal('0.00')

class CouponUsage(models.Model):
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, null=True, blank=True)
    
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} used {self.coupon.code}"

# NEW: Sales System Models
class BookSale(models.Model):
    """Model to manage book sales/discounts"""
    SALE_TYPES = (
        ('percentage', 'Percentage Discount'),
        ('fixed_amount', 'Fixed Amount Discount'),
    )
    
    name = models.CharField(max_length=100, help_text="Sale name (e.g., 'Summer Sale 2024')")
    description = models.TextField(blank=True)
    
    sale_type = models.CharField(max_length=20, choices=SALE_TYPES, default='percentage')
    discount_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Validity
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    
    # Books on sale
    books = models.ManyToManyField(Book, through='BookSaleItem', related_name='sales')
    
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def is_valid_now(self):
        """Check if sale is currently valid"""
        current_time = timezone.now()
        return (
            self.is_active and 
            self.valid_from <= current_time <= self.valid_to
        )

class BookSaleItem(models.Model):
    """Through model for books in sales with individual pricing"""
    sale = models.ForeignKey(BookSale, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    
    # Override sale discount for specific books if needed
    custom_discount_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Override the sale's default discount for this book"
    )
    custom_sale_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Set a specific sale price for this book"
    )
    
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('sale', 'book')
    
    def __str__(self):
        return f"{self.book.title} in {self.sale.name}"
    
    def get_sale_price(self):
        """Calculate the actual sale price for this book"""
        if self.custom_sale_price:
            return self.custom_sale_price
        
        original_price = self.book.price
        
        if self.custom_discount_value:
            discount_value = self.custom_discount_value
        else:
            discount_value = self.sale.discount_value
        
        if self.sale.sale_type == 'percentage':
            discount_amount = (original_price * discount_value) / 100
            return original_price - discount_amount
        else:  # fixed_amount
            return max(original_price - discount_value, Decimal('0.00'))
    
    def get_discount_percentage(self):
        """Get discount percentage for display"""
        original_price = self.book.price
        sale_price = self.get_sale_price()
        
        if original_price > sale_price:
            return round(((original_price - sale_price) / original_price) * 100)
        return 0