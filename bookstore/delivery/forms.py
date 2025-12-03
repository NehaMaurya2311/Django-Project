# delivery/forms.py
from django import forms
from .models import DeliveryPartner, Delivery, DeliveryUpdate

class DeliveryPartnerForm(forms.ModelForm):
    service_areas = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Enter pincodes separated by commas (e.g., 400001, 400002, 400003)'
        }),
        help_text="Enter pincodes separated by commas"
    )
    
    class Meta:
        model = DeliveryPartner
        fields = [
            'name', 'contact_person', 'phone', 'email', 'address',
            'service_areas', 'max_daily_deliveries', 'cost_per_delivery', 'status'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'max_daily_deliveries': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'cost_per_delivery': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean_service_areas(self):
        service_areas_str = self.cleaned_data.get('service_areas', '')
        if service_areas_str:
            # Split by comma and clean up
            areas = [area.strip() for area in service_areas_str.split(',') if area.strip()]
            return areas
        return []

class DeliveryStatusUpdateForm(forms.ModelForm):
    class Meta:
        model = DeliveryUpdate
        fields = ['status', 'location', 'description']
        widgets = {
            'status': forms.Select(
                choices=Delivery.DELIVERY_STATUS,
                attrs={'class': 'form-control'}
            ),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class AssignPartnerForm(forms.Form):
    partner = forms.ModelChoiceField(
        queryset=DeliveryPartner.objects.filter(status='active'),
        empty_label="Select delivery partner",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        delivery = kwargs.pop('delivery', None)
        super().__init__(*args, **kwargs)
        
        if delivery:
            # Filter partners that serve the delivery pincode
            pincode = delivery.order.shipping_pincode
            available_partners = DeliveryPartner.objects.filter(
                status='active',
                service_areas__contains=[pincode]
            )
            
            if available_partners.exists():
                self.fields['partner'].queryset = available_partners
            else:
                # If no partners serve this pincode, show all active partners
                self.fields['partner'].queryset = DeliveryPartner.objects.filter(status='active')

class BulkActionForm(forms.Form):
    ACTION_CHOICES = [
        ('', 'Select Action'),
        ('assign_partners', 'Auto-assign Partners'),
        ('update_status', 'Update Status'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # For status updates
    new_status = forms.ChoiceField(
        choices=[('', 'Select Status')] + list(Delivery.DELIVERY_STATUS),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class DeliveryFilterForm(forms.Form):
    STATUS_CHOICES = [('', 'All Status')] + list(Delivery.DELIVERY_STATUS)
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    partner = forms.ModelChoiceField(
        queryset=DeliveryPartner.objects.filter(status='active'),
        required=False,
        empty_label="All Partners",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by Order ID, Tracking ID, or Customer...'
        })
    )
    
    ordering = forms.ChoiceField(
        choices=[
            ('-created_at', 'Newest First'),
            ('created_at', 'Oldest First'),
            ('-estimated_delivery_time', 'Delivery Date (Latest)'),
            ('estimated_delivery_time', 'Delivery Date (Earliest)'),
            ('status', 'Status A-Z'),
            ('-status', 'Status Z-A'),
        ],
        initial='-created_at',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class CreateDeliveryForm(forms.Form):
    order_id = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter Order ID (e.g., ORD123ABC)'
        })
    )
    
    def clean_order_id(self):
        from orders.models import Order
        order_id = self.cleaned_data['order_id']
        
        try:
            order = Order.objects.get(order_id=order_id)
            if hasattr(order, 'delivery'):
                raise forms.ValidationError(f'Delivery already exists for Order #{order_id}')
            return order_id
        except Order.DoesNotExist:
            raise forms.ValidationError(f'Order #{order_id} not found')

class RatingForm(forms.Form):
    RATING_CHOICES = [
        (1, '1 - Very Poor'),
        (2, '2 - Poor'),
        (3, '3 - Average'),
        (4, '4 - Good'),
        (5, '5 - Excellent'),
    ]
    
    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    feedback = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Share your experience with the delivery...'
        })
    )