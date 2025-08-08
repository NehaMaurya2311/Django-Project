# reviews/admin.py
from django.contrib import admin
from django.utils import timezone
from .models import Review, ReviewHelpful, ReviewResponse

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['book', 'user', 'rating', 'status', 'is_verified_purchase', 'helpful_count', 'created_at']
    list_filter = ['status', 'rating', 'is_verified_purchase', 'created_at']
    search_fields = ['book__title', 'user__username', 'title', 'comment']
    readonly_fields = ['helpful_count', 'created_at', 'updated_at']
    
    actions = ['approve_reviews', 'reject_reviews']
    
    def approve_reviews(self, request, queryset):
        updated = queryset.filter(status='pending').update(
            status='approved',
            approved_at=timezone.now()
        )
        self.message_user(request, f'{updated} reviews were approved.')
    approve_reviews.short_description = 'Approve selected reviews'
    
    def reject_reviews(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f'{updated} reviews were rejected.')
    reject_reviews.short_description = 'Reject selected reviews'

admin.site.register(ReviewHelpful)
admin.site.register(ReviewResponse)