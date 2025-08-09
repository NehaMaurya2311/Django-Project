# support/admin.py
from django.contrib import admin
from .models import SupportCategory, SupportTicket, TicketResponse, LiveChat, ChatMessage, FAQCategory, FAQ

@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('order', 'name')

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'order', 'is_active', 'updated_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('question', 'answer', 'category__name')
    ordering = ('category', 'order', 'question')

@admin.register(SupportCategory)
class SupportCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

class TicketResponseInline(admin.TabularInline):
    model = TicketResponse
    extra = 0
    readonly_fields = ('created_at',)

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_id', 'subject', 'user', 'category', 'status', 'priority', 'assigned_to', 'created_at')
    list_filter = ('status', 'priority', 'category', 'created_at')
    search_fields = ('ticket_id', 'subject', 'user__username', 'user__email')
    readonly_fields = ('ticket_id', 'created_at', 'updated_at')
    inlines = [TicketResponseInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('ticket_id', 'user', 'category', 'subject', 'description')
        }),
        ('Status & Assignment', {
            'fields': ('status', 'priority', 'assigned_to', 'order')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'resolved_at')
        }),
        ('Customer Feedback', {
            'fields': ('rating', 'feedback')
        }),
    )

@admin.register(TicketResponse)
class TicketResponseAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'user', 'created_at', 'is_internal')
    list_filter = ('is_internal', 'created_at')
    search_fields = ('ticket__ticket_id', 'user__username', 'message')

class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('timestamp',)

@admin.register(LiveChat)
class LiveChatAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user', 'agent', 'status', 'started_at', 'ended_at')
    list_filter = ('status', 'started_at')
    search_fields = ('session_id', 'user__username', 'agent__username')
    readonly_fields = ('session_id', 'started_at')
    inlines = [ChatMessageInline]

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('chat', 'user', 'is_agent', 'timestamp')
    list_filter = ('is_agent', 'timestamp')
    search_fields = ('chat__session_id', 'user__username', 'message')
