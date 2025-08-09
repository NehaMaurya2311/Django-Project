# support/models.py
from django.db import models
from django.contrib.auth import get_user_model
from orders.models import Order

User = get_user_model()

class FAQCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "FAQ Categories"
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name

class FAQ(models.Model):
    category = models.ForeignKey(FAQCategory, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        ordering = ['order', 'question']

    def __str__(self):
        return self.question

class SupportCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Support Categories"
    
    def __str__(self):
        return self.name

class SupportTicket(models.Model):
    TICKET_STATUS = (
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('waiting_customer', 'Waiting for Customer'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )
    
    PRIORITY_LEVELS = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    )
    
    ticket_id = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_tickets')
    category = models.ForeignKey(SupportCategory, on_delete=models.SET_NULL, null=True)
    
    subject = models.CharField(max_length=200)
    description = models.TextField()
    
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, help_text="Related order if applicable")
    
    status = models.CharField(max_length=20, choices=TICKET_STATUS, default='open')
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Customer satisfaction
    rating = models.PositiveIntegerField(null=True, blank=True, help_text="1-5 rating")
    feedback = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"#{self.ticket_id} - {self.subject}"
    
    def save(self, *args, **kwargs):
        if not self.ticket_id:
            import uuid
            self.ticket_id = f"TK{str(uuid.uuid4())[:8].upper()}"
        super().save(*args, **kwargs)

class TicketResponse(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='responses')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    
    is_internal = models.BooleanField(default=False, help_text="Internal note, not visible to customer")
    attachment = models.FileField(upload_to='support_attachments/', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Response to {self.ticket.ticket_id}"

class LiveChat(models.Model):
    CHAT_STATUS = (
        ('waiting', 'Waiting for Agent'),
        ('active', 'Active'),
        ('ended', 'Ended'),
    )
    
    session_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    agent = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_sessions')
    
    status = models.CharField(max_length=20, choices=CHAT_STATUS, default='waiting')
    
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    # Customer satisfaction
    rating = models.PositiveIntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    
    def __str__(self):
        return f"Chat {self.session_id}"
    
    def save(self, *args, **kwargs):
        if not self.session_id:
            import uuid
            self.session_id = str(uuid.uuid4())
        super().save(*args, **kwargs)

class ChatMessage(models.Model):
    chat = models.ForeignKey(LiveChat, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    
    is_agent = models.BooleanField(default=False)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Message in {self.chat.session_id}"
