# logistics/forms.py
from django import forms
from django.contrib.auth import get_user_model
from .models import (
    LogisticsPartner, VendorPickup, DeliverySchedule, 
    StockReceiptConfirmation, DeliveryTracking, VendorLocation
)
from vendors.models import VendorProfile

User = get_user_model()

class LogisticsPartnerForm(forms.ModelForm):
    """Form for creating/editing logistics partners"""
    
    class Meta:
        model = LogisticsPartner
        fields = [
            'name', 'contact_person', 'phone', 'email', 'vehicle_type', 
            'vehicle_number', 'driver_license', 'service_areas', 
            'cost_per_km', 'base_cost', 'status'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Partner Company Name'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Person Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91-XXXXXXXXXX'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'partner@email.com'}),
            'vehicle_type': forms.Select(attrs={'class': 'form-select'}),
            'vehicle_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'MH12AB1234'}),
            'driver_license': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'License Number'}),
            'service_areas': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Enter service areas as JSON array: ["Mumbai", "Pune", "Nashik"]'
            }),
            'cost_per_km': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'base_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_service_areas(self):
        import json
        service_areas = self.cleaned_data.get('service_areas')
        if service_areas:
            try:
                # Try to parse as JSON
                if isinstance(service_areas, str):
                    parsed_areas = json.loads(service_areas)
                    if not isinstance(parsed_areas, list):
                        raise forms.ValidationError("Service areas must be a JSON array")
                    return parsed_areas
                return service_areas
            except json.JSONDecodeError:
                raise forms.ValidationError("Invalid JSON format for service areas")
        return []

class VendorPickupForm(forms.ModelForm):
    """Form for creating vendor pickups"""
    
    class Meta:
        model = VendorPickup
        fields = [
            'stock_offer', 'vendor', 'pickup_address', 'warehouse_address',
            'scheduled_date', 'estimated_distance', 'pickup_notes'
        ]
        widgets = {
            'stock_offer': forms.Select(attrs={'class': 'form-select'}),
            'vendor': forms.Select(attrs={'class': 'form-select'}),
            'pickup_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'warehouse_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'scheduled_date': forms.DateTimeInput(attrs={
                'class': 'form-control', 
                'type': 'datetime-local'
            }),
            'estimated_distance': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.01',
                'placeholder': 'Distance in KM'
            }),
            'pickup_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
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
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'special_instructions': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'Any special handling instructions...'
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

class StockReceiptForm(forms.ModelForm):
    """Form for staff to confirm stock receipt"""
    
    class Meta:
        model = StockReceiptConfirmation
        fields = [
            'books_received', 'books_accepted', 'books_rejected', 
            'rejection_reason', 'condition_rating', 'quality_notes'
        ]
        widgets = {
            'books_received': forms.NumberInput(attrs={'class': 'form-control'}),
            'books_accepted': forms.NumberInput(attrs={'class': 'form-control'}),
            'books_rejected': forms.NumberInput(attrs={'class': 'form-control', 'value': '0'}),
            'rejection_reason': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Reason for rejecting books (if any)...'
            }),
            'condition_rating': forms.Select(
                choices=[(i, f"{i} Star{'s' if i != 1 else ''}") for i in range(1, 6)],
                attrs={'class': 'form-select'}
            ),
            'quality_notes': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'Notes about book condition and quality...'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        books_received = cleaned_data.get('books_received', 0)
        books_accepted = cleaned_data.get('books_accepted', 0)
        books_rejected = cleaned_data.get('books_rejected', 0)

        if books_accepted + books_rejected != books_received:
            raise forms.ValidationError(
                "Accepted + Rejected books must equal total books received."
            )

        if books_rejected > 0 and not cleaned_data.get('rejection_reason'):
            raise forms.ValidationError(
                "Please provide a reason for rejecting books."
            )

        return cleaned_data

class DeliveryTrackingForm(forms.ModelForm):
    """Form for updating delivery tracking status"""
    
    class Meta:
        model = DeliveryTracking
        fields = ['status', 'location', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Current location or address'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': 'Update notes...'
            }),
        }

class VendorLocationForm(forms.ModelForm):
    """Form for vendors to add/edit their locations"""
    
    class Meta:
        model = VendorLocation
        fields = [
            'name', 'address', 'city', 'state', 'pincode',
            'contact_person', 'phone', 'is_primary', 'latitude', 'longitude'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Main Office, Warehouse 1'
            }),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': 'any',
                'placeholder': 'Optional: GPS latitude'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': 'any',
                'placeholder': 'Optional: GPS longitude'
            }),
        }

class AssignPartnerForm(forms.Form):
    """Form to assign logistics partner to delivery"""
    
    partner = forms.ModelChoiceField(
        queryset=LogisticsPartner.objects.filter(status='active'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select a logistics partner..."
    )
    
    estimated_pickup_time = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control', 
            'type': 'datetime-local'
        })
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control', 
            'rows': 3,
            'placeholder': 'Any special instructions for the partner...'
        })
    )