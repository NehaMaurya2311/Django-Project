# vendors/forms.py
from django import forms
from .models import VendorProfile, StockOffer, VendorTicket

class VendorRegistrationForm(forms.ModelForm):
    class Meta:
        model = VendorProfile
        exclude = ['user', 'status', 'rating']
        widgets = {
            'business_address': forms.Textarea(attrs={'rows': 3}),
            'website': forms.URLInput(),
            'email': forms.EmailInput(),
        }

class StockOfferForm(forms.ModelForm):
    class Meta:
        model = StockOffer
        fields = ['book', 'quantity', 'unit_price', 'availability_date', 'expiry_date', 'notes']
        widgets = {
            'availability_date': forms.DateInput(attrs={'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

class VendorTicketForm(forms.ModelForm):
    class Meta:
        model = VendorTicket
        fields = ['subject', 'category', 'description', 'priority']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
