# support/forms.py
from django import forms
from .models import SupportTicket, SupportCategory

class SupportTicketForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ['category', 'subject', 'description', 'order', 'priority']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['order'].queryset = user.orders.all()
        
        self.fields['category'].queryset = SupportCategory.objects.filter(is_active=True)
        self.fields['order'].required = False

class TicketResponseForm(forms.Form):
    message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Type your message here...'})
    )
    attachment = forms.FileField(required=False)