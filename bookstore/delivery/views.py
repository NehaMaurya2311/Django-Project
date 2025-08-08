from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from orders.models import Order
from .models import Delivery, DeliveryPartner, DeliveryUpdate

def is_staff_or_admin(user):
    return user.is_authenticated and user.user_type in ['staff', 'admin']

@login_required
def track_delivery(request, order_id):
    order = get_object_or_404(Order, order_id=order_id, user=request.user)
    
    try:
        delivery = order.delivery
        context = {
            'order': order,
            'delivery': delivery,
            'updates': delivery.updates.all()
        }
        return render(request, 'delivery/track_delivery.html', context)
    except Delivery.DoesNotExist:
        context = {'order': order}
        return render(request, 'delivery/no_delivery.html', context)

@login_required
@user_passes_test(is_staff_or_admin)
def delivery_dashboard(request):
    pending_deliveries = Delivery.objects.filter(status='assigned').count()
    in_transit_deliveries = Delivery.objects.filter(status__in=['picked_up', 'in_transit', 'out_for_delivery']).count()
    completed_deliveries = Delivery.objects.filter(status='delivered').count()
    
    recent_deliveries = Delivery.objects.select_related('order', 'delivery_partner').order_by('-created_at')[:10]
    
    context = {
        'pending_deliveries': pending_deliveries,
        'in_transit_deliveries': in_transit_deliveries,
        'completed_deliveries': completed_deliveries,
        'recent_deliveries': recent_deliveries,
    }
    
    return render(request, 'delivery/dashboard.html', context)