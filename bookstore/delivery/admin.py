from django.contrib import admin
from .models import DeliveryPartner, Delivery, DeliveryUpdate, DeliveryLocation

@admin.register(DeliveryPartner)
class DeliveryPartnerAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'phone', 'status', 'rating']
    list_filter = ['status']
    search_fields = ['name', 'contact_person', 'phone']

class DeliveryUpdateInline(admin.TabularInline):
    model = DeliveryUpdate
    extra = 0

@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ['order', 'delivery_partner', 'status', 'tracking_id', 'assigned_at']
    list_filter = ['status', 'delivery_partner']
    search_fields = ['order__order_id', 'tracking_id']
    inlines = [DeliveryUpdateInline]

admin.site.register(DeliveryLocation)