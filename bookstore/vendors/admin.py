# vendors/admin.py
from django.contrib import admin
from .models import VendorProfile, StockOffer, VendorTicket, VendorTicketResponse

@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'contact_person', 'status', 'rating', 'created_at']
    list_filter = ['status', 'city', 'state']
    search_fields = ['business_name', 'contact_person', 'email']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(StockOffer)
class StockOfferAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'book', 'quantity', 'unit_price', 'status', 'created_at']
    list_filter = ['status', 'vendor', 'created_at']
    search_fields = ['book__title', 'vendor__business_name']
    readonly_fields = ['total_amount', 'created_at', 'updated_at']

@admin.register(VendorTicket)
class VendorTicketAdmin(admin.ModelAdmin):
    list_display = ['ticket_id', 'vendor', 'subject', 'category', 'priority', 'status', 'created_at']
    list_filter = ['status', 'priority', 'category']
    search_fields = ['ticket_id', 'subject', 'vendor__business_name']
    readonly_fields = ['ticket_id', 'created_at', 'updated_at']

admin.site.register(VendorTicketResponse)