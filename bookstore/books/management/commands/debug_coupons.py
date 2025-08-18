# Create this file: books/management/commands/debug_coupons.py
# Run with: python manage.py debug_coupons

from django.core.management.base import BaseCommand
from django.utils import timezone
from coupons.models import Coupon
from books.models import Cart, User
from datetime import timedelta

class Command(BaseCommand):
    help = 'Debug coupon visibility issues'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== COUPON DEBUG REPORT ===\n'))
        
        # Check all coupons
        all_coupons = Coupon.objects.all()
        self.stdout.write(f"Total coupons in database: {all_coupons.count()}")
        
        if all_coupons.count() == 0:
            self.stdout.write(self.style.ERROR("❌ No coupons found in database!"))
            self.stdout.write("Create a test coupon:")
            self.stdout.write("1. Go to Django Admin")
            self.stdout.write("2. Add a new Coupon with:")
            self.stdout.write("   - Code: TEST10")
            self.stdout.write("   - Discount Type: percentage")
            self.stdout.write("   - Discount Value: 10")
            self.stdout.write("   - Valid From: yesterday")
            self.stdout.write("   - Valid To: tomorrow")
            self.stdout.write("   - Is Active: True")
            return
        
        current_time = timezone.now()
        
        for coupon in all_coupons:
            self.stdout.write(f"\n--- Coupon: {coupon.code} ---")
            self.stdout.write(f"Name: {coupon.name}")
            self.stdout.write(f"Is Active: {coupon.is_active}")
            self.stdout.write(f"Valid From: {coupon.valid_from}")
            self.stdout.write(f"Valid To: {coupon.valid_to}")
            self.stdout.write(f"Current Time: {current_time}")
            
            # Check basic validity
            if not coupon.is_active:
                self.stdout.write(self.style.ERROR("❌ Coupon is not active"))
                continue
            
            if current_time < coupon.valid_from:
                self.stdout.write(self.style.ERROR(f"❌ Coupon not yet valid (starts {coupon.valid_from})"))
                continue
            
            if current_time > coupon.valid_to:
                self.stdout.write(self.style.ERROR(f"❌ Coupon expired (ended {coupon.valid_to})"))
                continue
            
            self.stdout.write(self.style.SUCCESS("✅ Coupon is currently valid"))
            
            # Check restrictions
            if coupon.applicable_categories.exists():
                self.stdout.write(f"📋 Applies to categories: {list(coupon.applicable_categories.values_list('name', flat=True))}")
            
            if coupon.applicable_books.exists():
                self.stdout.write(f"📚 Applies to specific books: {coupon.applicable_books.count()} books")
            
            if not coupon.applicable_categories.exists() and not coupon.applicable_books.exists():
                self.stdout.write("🌐 Applies to all products")
            
            self.stdout.write(f"💰 Min Order Amount: ₹{coupon.min_order_amount}")
            self.stdout.write(f"🔢 Usage Limit Per User: {coupon.usage_limit_per_user}")
            
            if coupon.first_time_users_only:
                self.stdout.write("👤 First-time users only")
        
        # Test with a sample user and cart
        self.stdout.write(f"\n=== TESTING WITH SAMPLE USER ===")
        
        # Get first user or create one for testing
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR("❌ No users found. Create a user first."))
            return
        
        self.stdout.write(f"Testing with user: {user.username}")
        
        # Get or create cart
        cart, created = Cart.objects.get_or_create(user=user)
        
        if not cart.items.exists():
            self.stdout.write(self.style.WARNING("⚠️ User's cart is empty"))
            self.stdout.write("Add some books to cart to test coupon applicability")
        else:
            self.stdout.write(f"Cart has {cart.total_items} items, subtotal: ₹{cart.subtotal}")
            
            # Test each coupon
            applicable_coupons = cart.get_applicable_coupons(user)
            
            self.stdout.write(f"\nApplicable coupons for this cart: {len(applicable_coupons)}")
            
            for item in applicable_coupons:
                coupon = item['coupon']
                can_use = item['can_use']
                message = item['message']
                discount = item['discount_amount']
                
                status = "✅" if can_use else "❌"
                self.stdout.write(f"{status} {coupon.code}: {message}")
                if can_use:
                    self.stdout.write(f"   💰 Would save: ₹{discount}")
        
        # Quick fix suggestions
        self.stdout.write(f"\n=== QUICK FIXES ===")
        
        # Check for expired coupons
        expired_coupons = Coupon.objects.filter(valid_to__lt=current_time)
        if expired_coupons.exists():
            self.stdout.write(f"🔧 {expired_coupons.count()} expired coupons found. Update their valid_to date.")
        
        # Check for inactive coupons
        inactive_coupons = Coupon.objects.filter(is_active=False)
        if inactive_coupons.exists():
            self.stdout.write(f"🔧 {inactive_coupons.count()} inactive coupons found. Set is_active=True.")
        
        # Check for future coupons
        future_coupons = Coupon.objects.filter(valid_from__gt=current_time)
        if future_coupons.exists():
            self.stdout.write(f"🔧 {future_coupons.count()} future coupons found. Update their valid_from date.")
        
        self.stdout.write(f"\n=== TESTING COUPON VIEWS ===")
        
        # Test the view logic
        try:
            from django.test import RequestFactory
            from django.contrib.auth import get_user_model
            from coupons.views import available_coupons
            
            factory = RequestFactory()
            request = factory.get('/coupons/available/')
            request.user = user
            
            # This would test the view logic
            self.stdout.write("✅ View imports work correctly")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ View test failed: {e}"))
        
        self.stdout.write(f"\n=== NEXT STEPS ===")
        self.stdout.write("1. Check Django Admin for coupon settings")
        self.stdout.write("2. Verify coupon dates are correct")
        self.stdout.write("3. Ensure is_active=True")
        self.stdout.write("4. Add items to cart for testing")
        self.stdout.write("5. Check browser console for JavaScript errors")
        self.stdout.write("6. Verify URL patterns are correct")