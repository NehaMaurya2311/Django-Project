# coupons/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from books.models import Category, Book
from decimal import Decimal

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
    
    def can_use(self, user, order_amount=0):
        """Check if user can use this coupon"""
        from django.utils import timezone
        
        # Basic checks
        if not self.is_active:
            return False, "Coupon is not active"
        
        if timezone.now() < self.valid_from:
            return False, "Coupon is not yet valid"
        
        if timezone.now() > self.valid_to:
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
        
        return True, "Coupon is valid"
    
    def calculate_discount(self, order_amount):
        """Calculate discount amount for given order"""
        if self.discount_type == 'percentage':
            discount = (order_amount * self.discount_value) / 100
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
            return discount
        
        elif self.discount_type == 'fixed_amount':
            return min(self.discount_value, order_amount)
        
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
