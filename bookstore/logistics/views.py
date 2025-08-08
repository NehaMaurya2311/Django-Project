# logistics/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from .models import VendorPickup, LogisticsPartner, PickupTracking

def is_staff_or_admin(user):
    return user.is_authenticated and user.user_type in ['staff', 'admin']

@login_required
@user_passes_test(is_staff_or_admin)
def logistics_dashboard(request):
    scheduled_pickups = VendorPickup.objects.filter(status='scheduled').count()
    in_transit_pickups = VendorPickup.objects.filter(status='in_transit').count()
    completed_pickups = VendorPickup.objects.filter(status='delivered').count()
    
    recent_pickups = VendorPickup.objects.select_related(
        'vendor', 'logistics_partner', 'stock_offer__book'
    ).order_by('-created_at')[:10]
    
    context = {
        'scheduled_pickups': scheduled_pickups,
        'in_transit_pickups': in_transit_pickups,
        'completed_pickups': completed_pickups,
        'recent_pickups': recent_pickups,
    }
    
    return render(request, 'logistics/dashboard.html', context)

@login_required
@user_passes_test(is_staff_or_admin)
def pickup_list(request):
    pickups_list = VendorPickup.objects.select_related(
        'vendor', 'logistics_partner', 'stock_offer__book'
    ).order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter:
        pickups_list = pickups_list.filter(status=status_filter)
    
    paginator = Paginator(pickups_list, 20)
    page_number = request.GET.get('page')
    pickups = paginator.get_page(page_number)
    
    return render(request, 'logistics/pickup_list.html', {'pickups': pickups})

@login_required
@user_passes_test(is_staff_or_admin)
def pickup_detail(request, pickup_id):
    pickup = get_object_or_404(VendorPickup, id=pickup_id)
    return render(request, 'logistics/pickup_detail.html', {'pickup': pickup})
