# logistics/admin.py
from django.contrib import admin
from .models import LogisticsPartner, VendorPickup, PickupTracking, VendorLocation

@admin.register(LogisticsPartner)
class LogisticsPartnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'vehicle_type', 'vehicle_number', 'status', 'rating']
    list_filter = ['status', 'vehicle_type']
    search_fields = ['name', 'vehicle_number', 'phone']

class PickupTrackingInline(admin.TabularInline):
    model = PickupTracking
    extra = 0

@admin.register(VendorPickup)
class VendorPickupAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'stock_offer', 'logistics_partner', 'status', 'scheduled_date']
    list_filter = ['status', 'vendor']
    search_fields = ['vendor__business_name', 'stock_offer__book__title']
    inlines = [PickupTrackingInline]

admin.site.register(VendorLocation)
