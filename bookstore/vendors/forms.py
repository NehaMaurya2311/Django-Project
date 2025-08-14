# vendors/forms.py - Enhanced version
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import VendorProfile, StockOffer, VendorTicket
from logistics.models import VendorLocation, DeliverySchedule
from books.models import Book

User = get_user_model()

class VendorUserCreationForm(UserCreationForm):
    """Combined form for creating user account and vendor profile"""
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make email required
        self.fields['email'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        
        # Add styling classes and placeholders
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Choose a username'
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'your.email@company.com'
        })
        self.fields['first_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'First Name'
        })
        self.fields['last_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })

class VendorRegistrationForm(forms.ModelForm):
    """Enhanced vendor profile registration form"""
    
    class Meta:
        model = VendorProfile
        exclude = ['user', 'status', 'rating']
        widgets = {
            'business_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your Business Name'
            }),
            'business_registration_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Business Registration Number (optional)'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Primary Contact Person'
            }),
            'business_address': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Complete business address'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'State'
            }),
            'pincode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '400001'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+91-9876543210'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'business@company.com'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://yourwebsite.com (optional)'
            }),
            'business_license': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'GST Number (optional)'
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bank Name'
            }),
            'account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bank Account Number'
            }),
            'ifsc_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'IFSC Code'
            }),
        }

class StockOfferForm(forms.ModelForm):
    """Enhanced stock offer form with better validation"""
    
    class Meta:
        model = StockOffer
        fields = ['book', 'quantity', 'unit_price', 'availability_date', 'expiry_date', 'notes']
        widgets = {
            'book': forms.Select(attrs={
                'class': 'form-select',
                'data-live-search': 'true'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Number of books'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0.01',
                'placeholder': '0.00'
            }),
            'availability_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'expiry_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Additional notes about the books, condition, etc.'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter books that are active and available
        self.fields['book'].queryset = Book.objects.filter(
            status__in=['available', 'out_of_stock'],
        ).order_by('title')

    def clean(self):
        cleaned_data = super().clean()
        availability_date = cleaned_data.get('availability_date')
        expiry_date = cleaned_data.get('expiry_date')

        if availability_date and expiry_date:
            if expiry_date <= availability_date:
                raise forms.ValidationError(
                    "Expiry date must be after availability date."
                )

        return cleaned_data

class VendorTicketForm(forms.ModelForm):
    """Enhanced ticket form with categories"""
    
    class Meta:
        model = VendorTicket
        fields = ['subject', 'category', 'description', 'priority']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief subject line'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 5,
                'placeholder': 'Describe your issue in detail...'
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }

class VendorLocationForm(forms.ModelForm):
    """Form for vendors to manage their pickup/delivery locations"""
    
    class Meta:
        model = VendorLocation
        exclude = ['vendor']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Main Office, Warehouse 1, Store 2'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Complete address for pickup/delivery'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'State'
            }),
            'pincode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '400001'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contact person at this location'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+91-9876543210'
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 'any',
                'placeholder': 'GPS Latitude (optional)'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 'any',
                'placeholder': 'GPS Longitude (optional)'
            }),
        }

class DeliveryScheduleForm(forms.ModelForm):
    """Form for vendors to schedule deliveries"""
    
    class Meta:
        model = DeliverySchedule
        fields = [
            'scheduled_delivery_date', 'vendor_location', 'contact_person',
            'contact_phone', 'special_instructions'
        ]
        widgets = {
            'scheduled_delivery_date': forms.DateTimeInput(attrs={
                'class': 'form-control', 
                'type': 'datetime-local'
            }),
            'vendor_location': forms.Select(attrs={'class': 'form-select'}),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Person available at pickup location'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+91-9876543210'
            }),
            'special_instructions': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'Any special handling instructions, access directions, preferred time slots, etc.'
            }),
        }

    def __init__(self, *args, **kwargs):
        vendor = kwargs.pop('vendor', None)
        super().__init__(*args, **kwargs)
        
        if vendor:
            # Filter locations for the specific vendor
            self.fields['vendor_location'].queryset = VendorLocation.objects.filter(
                vendor=vendor, is_active=True
            )

class VendorProfileUpdateForm(forms.ModelForm):
    """Form for vendors to update their profile"""
    
    class Meta:
        model = VendorProfile
        exclude = ['user', 'status', 'rating', 'created_at', 'updated_at']
        widgets = {
            'business_name': forms.TextInput(attrs={'class': 'form-control'}),
            'business_registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'business_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'business_license': forms.FileInput(attrs={'class': 'form-control'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'ifsc_code': forms.TextInput(attrs={'class': 'form-control'}),
        }

class OfferDeliveryDetailsForm(forms.ModelForm):
    """Form for vendors to add delivery details to approved offers"""
    
    class Meta:
        model = StockOffer
        fields = [
            'vendor_delivery_date', 'vendor_contact_person', 'vendor_contact_phone'
        ]
        widgets = {
            'vendor_delivery_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'vendor_contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contact person for delivery coordination'
            }),
            'vendor_contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+91-9876543210'
            }),
        }