# wishlist/admin.py
from django.contrib import admin
from .models import WishlistItem, WishlistCollection, WishlistCollectionItem

@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ['user', 'book', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__username', 'book__title']

@admin.register(WishlistCollection)
class WishlistCollectionAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'privacy', 'is_default', 'created_at']
    list_filter = ['privacy', 'is_default', 'created_at']
    search_fields = ['user__username', 'name']

admin.site.register(WishlistCollectionItem)