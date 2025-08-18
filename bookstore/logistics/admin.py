# logistics/admin.py - FIXED VERSION
from django.contrib import admin
from .models import (
    LogisticsPartner, VendorPickup, PickupTracking, VendorLocation,
    DeliverySchedule, DeliveryTracking, StockReceiptConfirmation
)


@admin.register(LogisticsPartner)
class LogisticsPartnerAdmin(admin.ModelAdmin):
    list_display = (
        "name", "contact_person", "phone", "email", 
        "vehicle_type", "vehicle_number", 
        "status", "rating", "cost_per_km", "base_cost", 
        "created_at"
    )
    list_filter = ("status", "vehicle_type", "service_areas", "created_at")
    search_fields = ("name", "contact_person", "phone", "email", "vehicle_number", "driver_license")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    list_editable = ("status", "rating", "cost_per_km", "base_cost")

    fieldsets = (
        ("Basic Info", {
            "fields": ("name", "contact_person", "phone", "email", "status", "rating")
        }),
        ("Vehicle Details", {
            "fields": ("vehicle_type", "vehicle_number", "driver_license")
        }),
        ("Service & Pricing", {
            "fields": ("service_areas", "cost_per_km", "base_cost")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )

class PickupTrackingInline(admin.TabularInline):
    model = PickupTracking
    extra = 0
    readonly_fields = ['timestamp']

@admin.register(VendorPickup)
class VendorPickupAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'stock_offer', 'logistics_partner', 'status', 'scheduled_date']
    list_filter = ['status', 'vendor']
    search_fields = ['vendor__business_name', 'stock_offer__book__title']
    inlines = [PickupTrackingInline]

class DeliveryTrackingInline(admin.TabularInline):
    model = DeliveryTracking
    extra = 0
    readonly_fields = ['timestamp']
    fields = ['status', 'location', 'notes', 'updated_by', 'timestamp']

@admin.register(DeliverySchedule)
class DeliveryScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'vendor', 'stock_offer_book', 'status', 
        'scheduled_delivery_date', 'assigned_partner'
    ]
    list_filter = [
        'status', 'vendor', 'assigned_partner', 
        'scheduled_delivery_date', 'created_at'
    ]
    search_fields = [
        'vendor__business_name', 'stock_offer__book__title',
        'contact_person', 'assigned_partner__name'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'confirmed_at', 
        'actual_pickup_time', 'actual_delivery_time', 'completed_at'
    ]
    inlines = [DeliveryTrackingInline]
    
    def stock_offer_book(self, obj):
        return obj.stock_offer.book.title
    stock_offer_book.short_description = 'Book'
    stock_offer_book.admin_order_field = 'stock_offer__book__title'
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'stock_offer', 'vendor', 'status'
            )
        }),
        ('Delivery Details', {
            'fields': (
                'scheduled_delivery_date', 'vendor_location',
                'contact_person', 'contact_phone', 'special_instructions'
            )
        }),
        ('Logistics Assignment', {
            'fields': (
                'assigned_partner', 'estimated_pickup_time', 
                'estimated_delivery_time'
            )
        }),
        ('Actual Times', {
            'fields': (
                'actual_pickup_time', 'actual_delivery_time', 
                'completed_at', 'confirmed_at'
            ),
            'classes': ('collapse',)
        }),
        ('Verification', {
            'fields': (
                'delivered_quantity', 'verified_quantity', 'quality_notes'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(DeliveryTracking)
class DeliveryTrackingAdmin(admin.ModelAdmin):
    list_display = [
        'delivery_info', 'status', 'timestamp', 'updated_by', 'location'
    ]
    list_filter = ['status', 'timestamp', 'updated_by']
    search_fields = [
        'delivery__id', 'delivery__vendor__business_name', 
        'delivery__stock_offer__book__title', 'location', 'notes'
    ]
    readonly_fields = ['timestamp']
    
    def delivery_info(self, obj):
        """Show delivery ID with vendor and book info"""
        delivery = obj.delivery
        book_title = delivery.stock_offer.book.title[:30] + "..." if len(delivery.stock_offer.book.title) > 30 else delivery.stock_offer.book.title
        return f"#{delivery.id} - {delivery.vendor.business_name} - {book_title}"
    
    delivery_info.short_description = 'Delivery Details'
    delivery_info.admin_order_field = 'delivery__id'

    # Optional: Add custom admin actions
    actions = ['mark_as_collected', 'mark_as_in_transit', 'mark_as_arrived']
    
    def mark_as_collected(self, request, queryset):
        updated = queryset.update(status='collected')
        self.message_user(request, f'{updated} tracking updates marked as collected.')
    mark_as_collected.short_description = "Mark selected as collected"
    
    def mark_as_in_transit(self, request, queryset):
        updated = queryset.update(status='in_transit')
        self.message_user(request, f'{updated} tracking updates marked as in transit.')
    mark_as_in_transit.short_description = "Mark selected as in transit"
    
    def mark_as_arrived(self, request, queryset):
        updated = queryset.update(status='arrived')
        self.message_user(request, f'{updated} tracking updates marked as arrived.')
    mark_as_arrived.short_description = "Mark selected as arrived"

@admin.register(StockReceiptConfirmation)
class StockReceiptConfirmationAdmin(admin.ModelAdmin):
    list_display = [
        'delivery_schedule_id', 'received_by_staff', 'books_received', 
        'books_accepted', 'books_rejected', 'confirmed_at'
    ]
    list_filter = ['confirmed_at', 'received_by_staff', 'stock_updated']
    search_fields = [
        'delivery_schedule__vendor__business_name',
        'delivery_schedule__stock_offer__book__title'
    ]
    readonly_fields = ['confirmed_at']
    
    def delivery_schedule_id(self, obj):
        return f"#{obj.delivery_schedule.id}"
    delivery_schedule_id.short_description = 'Delivery'
    
    fieldsets = (
        ('Delivery Information', {
            'fields': ('delivery_schedule', 'received_by_staff')
        }),
        ('Quantity Verification', {
            'fields': (
                'books_received', 'books_accepted', 'books_rejected', 
                'rejection_reason'
            )
        }),
        ('Quality Assessment', {
            'fields': ('condition_rating', 'quality_notes')
        }),
        ('System Updates', {
            'fields': (
                'stock_updated', 'stock_movement_created', 'confirmed_at'
            ),
            'classes': ('collapse',)
        })
    )

@admin.register(VendorLocation)
class VendorLocationAdmin(admin.ModelAdmin):
    list_display = [
        'vendor', 'name', 'city', 'state', 'is_primary', 'is_active'
    ]
    list_filter = ['is_primary', 'is_active', 'state', 'city']
    search_fields = [
        'vendor__business_name', 'name', 'address', 'city'
    ]
    
    fieldsets = (
        ('Location Details', {
            'fields': ('vendor', 'name', 'address', 'city', 'state', 'pincode')
        }),
        ('Contact Information', {
            'fields': ('contact_person', 'phone')
        }),
        ('Status & Coordinates', {
            'fields': ('is_primary', 'is_active', 'latitude', 'longitude')
        })
    )