# orders/forms.py
from django import forms
from .models import Order, Return

class CheckoutForm(forms.Form):
    # Billing Information
    billing_first_name = forms.CharField(max_length=100)
    billing_last_name = forms.CharField(max_length=100)
    billing_email = forms.EmailField()
    billing_phone = forms.CharField(max_length=15)
    billing_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
    billing_city = forms.CharField(max_length=100)
    billing_state = forms.CharField(max_length=100)
    billing_pincode = forms.CharField(max_length=10)
    
    # Shipping Information
    same_as_billing = forms.BooleanField(required=False, initial=True)
    shipping_first_name = forms.CharField(max_length=100, required=False)
    shipping_last_name = forms.CharField(max_length=100, required=False)
    shipping_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    shipping_city = forms.CharField(max_length=100, required=False)
    shipping_state = forms.CharField(max_length=100, required=False)
    shipping_pincode = forms.CharField(max_length=10, required=False)
    
    # Additional
    coupon_code = forms.CharField(max_length=50, required=False)
    notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False)

class ReturnRequestForm(forms.ModelForm):
    class Meta:
        model = Return
        fields = ['reason', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }
