# Create this file: books/management/commands/create_test_coupon.py
# Run with: python manage.py create_test_coupon

from django.core.management.base import BaseCommand
from django.utils import timezone
from coupons.models import Coupon
from datetime import timedelta

class Command(BaseCommand):
    help = 'Create a test coupon for debugging'

    def handle(self, *args, **options):
        # Delete any existing test coupons
        Coupon.objects.filter(code__startswith='TEST').delete()
        
        # Create a simple test coupon
        now = timezone.now()
        
        coupon = Coupon.objects.create(
            code='TEST10',
            name='Test 10% Discount',
            description='Test coupon for debugging - 10% off on all items',
            discount_type='percentage',
            discount_value=10.00,
            min_order_amount=0.00,
            usage_limit_per_user=5,
            valid_from=now - timedelta(days=1),  # Valid from yesterday
            valid_to=now + timedelta(days=30),   # Valid for 30 days
            first_time_users_only=False,
            is_active=True
        )
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created test coupon: {coupon.code}'))
        self.stdout.write(f'Valid from: {coupon.valid_from}')
        self.stdout.write(f'Valid to: {coupon.valid_to}')
        self.stdout.write(f'Discount: {coupon.discount_value}% off')
        self.stdout.write(f'Min order: ₹{coupon.min_order_amount}')
        
        # Create another fixed amount coupon
        coupon2 = Coupon.objects.create(
            code='TEST50',
            name='Test ₹50 Off',
            description='Test coupon - ₹50 off on orders above ₹200',
            discount_type='fixed_amount',
            discount_value=50.00,
            min_order_amount=200.00,
            usage_limit_per_user=3,
            valid_from=now - timedelta(days=1),
            valid_to=now + timedelta(days=30),
            first_time_users_only=False,
            is_active=True
        )
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created test coupon: {coupon2.code}'))
        self.stdout.write(f'Discount: ₹{coupon2.discount_value} off')
        self.stdout.write(f'Min order: ₹{coupon2.min_order_amount}')
        
        self.stdout.write(f'\n🧪 Test these coupons in your cart:')
        self.stdout.write(f'1. Add books worth ≥₹200 to cart')
        self.stdout.write(f'2. Try coupon codes: TEST10, TEST50')
        self.stdout.write(f'3. Check /coupons/available/ page')