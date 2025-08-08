
# warehouse/admin.py
from django.contrib import admin
from .models import Stock, StockMovement, CategoryStock, InventoryAudit, InventoryAuditItem

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['book', 'quantity', 'reserved_quantity', 'available_quantity', 'reorder_level', 'needs_reorder']
    list_filter = ['book__category', 'book__status']
    search_fields = ['book__title', 'book__isbn']
    readonly_fields = ['available_quantity', 'needs_reorder']

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['stock', 'movement_type', 'quantity', 'reference', 'performed_by', 'created_at']
    list_filter = ['movement_type', 'created_at']
    search_fields = ['stock__book__title', 'reference']

admin.site.register(CategoryStock)
admin.site.register(InventoryAudit)
admin.site.register(InventoryAuditItem)