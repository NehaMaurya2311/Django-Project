# coupons/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Coupon, CouponUsage, BookSale, BookSaleItem

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'name', 'discount_display', 'validity_status', 
        'usage_count', 'min_order_amount', 'is_active'
    ]
    list_filter = ['discount_type', 'is_active', 'first_time_users_only']
    search_fields = ['code', 'name', 'description']
    filter_horizontal = ['applicable_categories', 'applicable_books', 'excluded_users']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'description', 'is_active')
        }),
        ('Discount Settings', {
            'fields': ('discount_type', 'discount_value', 'max_discount_amount')
        }),
        ('Usage Restrictions', {
            'fields': ('min_order_amount', 'usage_limit', 'usage_limit_per_user')
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_to')
        }),
        ('Applicability', {
            'fields': ('applicable_categories', 'applicable_books'),
            'classes': ('collapse',)
        }),
        ('User Restrictions', {
            'fields': ('first_time_users_only', 'excluded_users'),
            'classes': ('collapse',)
        }),
    )
    
    def discount_display(self, obj):
        if obj.discount_type == 'percentage':
            return f'{obj.discount_value}% OFF'
        elif obj.discount_type == 'fixed_amount':
            return f'₹{obj.discount_value} OFF'
        else:
            return 'FREE SHIPPING'
    discount_display.short_description = 'Discount'
    
    def validity_status(self, obj):
        now = timezone.now()
        if not obj.is_active:
            return format_html('<span style="color: red;">❌ Inactive</span>')
        elif now < obj.valid_from:
            return format_html('<span style="color: orange;">⏳ Future</span>')
        elif now > obj.valid_to:
            return format_html('<span style="color: red;">❌ Expired</span>')
        else:
            return format_html('<span style="color: green;">✅ Active</span>')
    validity_status.short_description = 'Status'
    
    def usage_count(self, obj):
        count = obj.usages.count()
        limit = obj.usage_limit
        if limit:
            return f'{count}/{limit}'
        return str(count)
    usage_count.short_description = 'Used'
    
    actions = ['activate_coupons', 'deactivate_coupons', 'extend_validity']
    
    def activate_coupons(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} coupons activated.')
    activate_coupons.short_description = "Activate selected coupons"
    
    def deactivate_coupons(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} coupons deactivated.')
    deactivate_coupons.short_description = "Deactivate selected coupons"
    
    def extend_validity(self, request, queryset):
        from datetime import timedelta
        for coupon in queryset:
            if coupon.valid_to < timezone.now():
                coupon.valid_to = timezone.now() + timedelta(days=30)
                coupon.save()
        self.message_user(request, f'Extended validity for expired coupons.')
    extend_validity.short_description = "Extend validity of expired coupons"

@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ['coupon', 'user', 'discount_amount', 'used_at']
    list_filter = ['used_at', 'coupon']
    search_fields = ['coupon__code', 'user__username', 'user__email']
    readonly_fields = ['used_at']

@admin.register(BookSale)
class BookSaleAdmin(admin.ModelAdmin):
    list_display = ['name', 'sale_type', 'discount_value', 'book_count', 'validity_status', 'is_active']
    list_filter = ['sale_type', 'is_active']
    search_fields = ['name', 'description']
    
    def book_count(self, obj):
        return obj.books.count()
    book_count.short_description = 'Books'
    
    def validity_status(self, obj):
        if obj.is_valid_now():
            return format_html('<span style="color: green;">✅ Active</span>')
        else:
            return format_html('<span style="color: red;">❌ Inactive</span>')
    validity_status.short_description = 'Status'

@admin.register(BookSaleItem)
class BookSaleItemAdmin(admin.ModelAdmin):
    list_display = ['book', 'sale', 'original_price', 'sale_price', 'discount_percentage']
    list_filter = ['sale']
    search_fields = ['book__title', 'sale__name']
    
    def original_price(self, obj):
        return f'₹{obj.book.price}'
    original_price.short_description = 'Original Price'
    
    def sale_price(self, obj):
        return f'₹{obj.get_sale_price()}'
    sale_price.short_description = 'Sale Price'
    
    def discount_percentage(self, obj):
        return f'{obj.get_discount_percentage()}%'
    discount_percentage.short_description = 'Discount %'