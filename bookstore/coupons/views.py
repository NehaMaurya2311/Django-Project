# coupons/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from .models import Coupon
import json

@login_required
def validate_coupon(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        coupon_code = data.get('coupon_code', '').upper()
        order_amount = float(data.get('order_amount', 0))
        
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            is_valid, message = coupon.can_use(request.user, order_amount)
            
            if is_valid:
                discount_amount = coupon.calculate_discount(order_amount)
                return JsonResponse({
                    'valid': True,
                    'message': 'Coupon applied successfully!',
                    'discount_amount': float(discount_amount),
                    'discount_type': coupon.discount_type,
                    'new_total': float(order_amount - discount_amount)
                })
            else:
                return JsonResponse({
                    'valid': False,
                    'message': message
                })
                
        except Coupon.DoesNotExist:
            return JsonResponse({
                'valid': False,
                'message': 'Invalid coupon code'
            })
    
    return JsonResponse({'valid': False, 'message': 'Invalid request'})

@login_required
def available_coupons(request):
    """Show available coupons for the user"""
    from django.db.models import Q
    
    current_time = timezone.now()
    
    # Get coupons that user can potentially use
    available_coupons = Coupon.objects.filter(
        is_active=True,
        valid_from__lte=current_time,
        valid_to__gte=current_time
    ).exclude(
        excluded_users=request.user
    )
    
    # Filter out coupons user has already used max times
    valid_coupons = []
    for coupon in available_coupons:
        user_usage = coupon.usages.filter(user=request.user).count()
        if user_usage < coupon.usage_limit_per_user:
            valid_coupons.append(coupon)
    
    return render(request, 'coupons/available_coupons.html', {'coupons': valid_coupons})
