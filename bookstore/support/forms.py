# support/forms.py
from django import forms
from .models import SupportTicket, TicketResponse, SupportCategory
from orders.models import Order

class SupportTicketForm(forms.ModelForm):
    """Form for creating support tickets"""
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        
        # Customize form fields
        self.fields['category'].queryset = SupportCategory.objects.filter(is_active=True)
        self.fields['category'].empty_label = "Select a category"
        
        # If user is provided, filter orders to user's orders
        if user and user.is_authenticated:
            self.fields['order'].queryset = Order.objects.filter(user=user).order_by('-created_at')
            self.fields['order'].empty_label = "Select related order (optional)"
        else:
            self.fields['order'].queryset = Order.objects.none()
        
        # Add CSS classes and attributes
        self.fields['subject'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Brief description of your issue'
        })
        
        self.fields['description'].widget.attrs.update({
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Please provide detailed information about your issue'
        })
        
        self.fields['category'].widget.attrs.update({
            'class': 'form-select'
        })
        
        self.fields['order'].widget.attrs.update({
            'class': 'form-select'
        })
        
        self.fields['priority'].widget.attrs.update({
            'class': 'form-select'
        })
    
    class Meta:
        model = SupportTicket
        fields = ['category', 'subject', 'description', 'order', 'priority']
        
    def clean_subject(self):
        subject = self.cleaned_data.get('subject')
        if subject and len(subject) < 5:
            raise forms.ValidationError('Subject must be at least 5 characters long.')
        return subject
    
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description and len(description) < 10:
            raise forms.ValidationError('Description must be at least 10 characters long.')
        return description

class TicketResponseForm(forms.ModelForm):
    """Form for responding to support tickets"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes and attributes
        self.fields['message'].widget.attrs.update({
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Type your message here...'
        })
        
        self.fields['attachment'].widget.attrs.update({
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.gif'
        })
    
    class Meta:
        model = TicketResponse
        fields = ['message', 'attachment']
        
    def clean_message(self):
        message = self.cleaned_data.get('message')
        if message and len(message.strip()) < 3:
            raise forms.ValidationError('Message must be at least 3 characters long.')
        return message

class TicketFilterForm(forms.Form):
    """Form for filtering support tickets"""
    
    STATUS_CHOICES = [('', 'All Statuses')] + list(SupportTicket.TICKET_STATUS)
    PRIORITY_CHOICES = [('', 'All Priorities')] + list(SupportTicket.PRIORITY_LEVELS)
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    priority = forms.ChoiceField(
        choices=PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    category = forms.ModelChoiceField(
        queryset=SupportCategory.objects.filter(is_active=True),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class AdminTicketResponseForm(TicketResponseForm):
    """Extended form for admin ticket responses"""
    
    is_internal = forms.BooleanField(
        required=False,
        label='Internal Note',
        help_text='Check this if the message is an internal note (not visible to customer)',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    new_status = forms.ChoiceField(
        choices=[('', 'Keep Current Status')] + list(SupportTicket.TICKET_STATUS),
        required=False,
        label='Update Status',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = TicketResponse
        fields = ['message', 'attachment', 'is_internal']

class TicketRatingForm(forms.ModelForm):
    """Form for rating ticket resolution"""
    
    RATING_CHOICES = [
        (1, '⭐ Poor'),
        (2, '⭐⭐ Fair'),
        (3, '⭐⭐⭐ Good'),
        (4, '⭐⭐⭐⭐ Very Good'),
        (5, '⭐⭐⭐⭐⭐ Excellent'),
    ]
    
    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='How would you rate our support?'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['feedback'].widget.attrs.update({
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional: Tell us more about your experience'
        })
        
        self.fields['feedback'].required = False
    
    class Meta:
        model = SupportTicket
        fields = ['rating', 'feedback']

class ChatbotTicketForm(forms.Form):
    """Simple form for creating tickets through chatbot"""
    
    category_id = forms.IntegerField(widget=forms.HiddenInput())
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Brief description of your issue'
        })
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Please describe your issue in detail'
        })
    )
    
    def clean_subject(self):
        subject = self.cleaned_data.get('subject')
        if subject and len(subject.strip()) < 5:
            raise forms.ValidationError('Subject must be at least 5 characters long.')
        return subject.strip()
    
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if description and len(description.strip()) < 10:
            raise forms.ValidationError('Description must be at least 10 characters long.')
        return description.strip()
    
    def clean_category_id(self):
        category_id = self.cleaned_data.get('category_id')
        if not SupportCategory.objects.filter(id=category_id, is_active=True).exists():
            raise forms.ValidationError('Invalid category selected.')
        return category_id