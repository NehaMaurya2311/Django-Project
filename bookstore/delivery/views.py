# delivery/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.db import transaction
from orders.models import Order
from .models import Delivery, DeliveryPartner, DeliveryUpdate, DeliveryLocation
from datetime import datetime, timedelta
import json

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
    # Get delivery statistics
    pending_deliveries = Delivery.objects.filter(status='assigned').count()
    in_transit_deliveries = Delivery.objects.filter(
        status__in=['picked_up', 'in_transit', 'out_for_delivery']
    ).count()
    completed_deliveries = Delivery.objects.filter(status='delivered').count()
    failed_deliveries = Delivery.objects.filter(status__in=['failed', 'returned']).count()
    
    # Get recent deliveries with related data
    recent_deliveries = Delivery.objects.select_related(
        'order', 
        'order__user', 
        'delivery_partner'
    ).order_by('-created_at')[:10]
    
    # Get partner statistics
    active_partners = DeliveryPartner.objects.filter(status='active').count()
    total_partners = DeliveryPartner.objects.count()
    
    context = {
        'pending_deliveries': pending_deliveries,
        'in_transit_deliveries': in_transit_deliveries,
        'completed_deliveries': completed_deliveries,
        'failed_deliveries': failed_deliveries,
        'recent_deliveries': recent_deliveries,
        'active_partners': active_partners,
        'total_partners': total_partners,
    }
    
    return render(request, 'delivery/dashboard.html', context)

@login_required
@user_passes_test(is_staff_or_admin)
def delivery_list(request):
    """Enhanced delivery list with filtering and pagination"""
    deliveries = Delivery.objects.select_related(
        'order', 
        'order__user', 
        'delivery_partner'
    ).order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        deliveries = deliveries.filter(status=status_filter)
    
    # Filter by partner
    partner_filter = request.GET.get('partner')
    if partner_filter:
        deliveries = deliveries.filter(delivery_partner_id=partner_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        deliveries = deliveries.filter(
            Q(order__order_id__icontains=search_query) |
            Q(tracking_id__icontains=search_query) |
            Q(order__user__first_name__icontains=search_query) |
            Q(order__user__last_name__icontains=search_query) |
            Q(order__user__email__icontains=search_query)
        )
    
    # Ordering
    ordering = request.GET.get('ordering', '-created_at')
    if ordering:
        deliveries = deliveries.order_by(ordering)
    
    # Pagination
    paginator = Paginator(deliveries, 20)
    page_number = request.GET.get('page')
    deliveries_page = paginator.get_page(page_number)
    
    # Get delivery partners for filter dropdown
    delivery_partners = DeliveryPartner.objects.filter(status='active')
    
    context = {
        'deliveries': deliveries_page,
        'delivery_partners': delivery_partners,
        'is_paginated': deliveries_page.has_other_pages(),
        'page_obj': deliveries_page,
    }
    
    return render(request, 'delivery/delivery_list.html', context)

@login_required
@user_passes_test(is_staff_or_admin)
def update_delivery_status(request, delivery_id):
    """Update delivery status and create tracking update"""
    if request.method == 'POST':
        delivery = get_object_or_404(Delivery, id=delivery_id)
        
        new_status = request.POST.get('status')
        location = request.POST.get('location', '')
        description = request.POST.get('description', '')
        
        if new_status in [choice[0] for choice in Delivery.DELIVERY_STATUS]:
            old_status = delivery.status
            delivery.status = new_status
            
            # Set timestamps based on status
            if new_status == 'picked_up' and not delivery.picked_up_at:
                delivery.picked_up_at = datetime.now()
            elif new_status == 'delivered' and not delivery.delivered_at:
                delivery.delivered_at = datetime.now()
                delivery.actual_delivery_time = datetime.now()
            
            delivery.save()
            
            # Create delivery update
            DeliveryUpdate.objects.create(
                delivery=delivery,
                status=new_status,
                location=location,
                description=description or f"Status updated from {old_status} to {new_status}"
            )
            
            # Update order status if needed
            if new_status == 'delivered':
                delivery.order.status = 'delivered'
                delivery.order.delivered_at = datetime.now()
                delivery.order.save()
            
            messages.success(request, f'Delivery status updated to {delivery.get_status_display()}')
        else:
            messages.error(request, 'Invalid status provided')
    
    return redirect('delivery:delivery_list')

@login_required
@user_passes_test(is_staff_or_admin)
def assign_partner(request, delivery_id):
    """Assign or reassign delivery partner"""
    if request.method == 'POST':
        delivery = get_object_or_404(Delivery, id=delivery_id)
        partner_id = request.POST.get('partner_id')
        
        if partner_id:
            partner = get_object_or_404(DeliveryPartner, id=partner_id, status='active')
            
            # Check if partner can take more deliveries
            if not partner.can_take_delivery():
                messages.error(request, f'{partner.name} has reached maximum delivery capacity for today')
                return redirect('delivery:delivery_list')
            
            old_partner = delivery.delivery_partner
            delivery.delivery_partner = partner
            delivery.delivery_cost = float(partner.cost_per_delivery) if partner.cost_per_delivery > 0 else delivery.delivery_cost
            delivery.save()
            
            # Create tracking update
            DeliveryUpdate.objects.create(
                delivery=delivery,
                status=delivery.status,
                description=f"Delivery partner {'changed' if old_partner else 'assigned'}: {partner.name}"
            )
            
            messages.success(request, f'Delivery assigned to {partner.name}')
        else:
            # Unassign partner
            delivery.delivery_partner = None
            delivery.save()
            messages.success(request, 'Delivery partner unassigned')
    
    return redirect('delivery:delivery_list')

@login_required
@user_passes_test(is_staff_or_admin)
def partner_list(request):
    """List all delivery partners with statistics"""
    partners = DeliveryPartner.objects.annotate(
        total_deliveries=Count('deliveries'),
        pending_deliveries=Count('deliveries', filter=Q(deliveries__status='assigned')),
        completed_deliveries=Count('deliveries', filter=Q(deliveries__status='delivered'))
    ).order_by('-created_at')
    
    context = {
        'partners': partners
    }
    
    return render(request, 'delivery/partner_list.html', context)

@login_required
@user_passes_test(is_staff_or_admin)
def create_partner(request):
    """Create a new delivery partner"""
    if request.method == 'POST':
        try:
            # Get form data
            name = request.POST.get('name')
            contact_person = request.POST.get('contact_person')
            phone = request.POST.get('phone')
            email = request.POST.get('email')
            address = request.POST.get('address')
            max_daily_deliveries = request.POST.get('max_daily_deliveries', 50)
            cost_per_delivery = request.POST.get('cost_per_delivery', 0.00)
            service_areas = request.POST.get('service_areas', '').split(',')
            
            # Clean service areas
            service_areas = [area.strip() for area in service_areas if area.strip()]
            
            # Validate required fields
            if not all([name, contact_person, phone, email, address]):
                messages.error(request, 'Please fill in all required fields.')
                return render(request, 'delivery/create_partner.html')
            
            # Create partner
            partner = DeliveryPartner.objects.create(
                name=name,
                contact_person=contact_person,
                phone=phone,
                email=email,
                address=address,
                service_areas=service_areas,
                max_daily_deliveries=int(max_daily_deliveries),
                cost_per_delivery=float(cost_per_delivery),
                status='active'
            )
            
            messages.success(request, f'Delivery partner "{partner.name}" created successfully!')
            return redirect('delivery:partner_list')
            
        except ValueError as e:
            messages.error(request, 'Invalid number format in max deliveries or cost fields.')
        except Exception as e:
            messages.error(request, f'Error creating partner: {str(e)}')
    
    return render(request, 'delivery/create_partner.html')

@login_required
@user_passes_test(is_staff_or_admin)
def edit_partner(request, partner_id):
    """Edit an existing delivery partner"""
    partner = get_object_or_404(DeliveryPartner, id=partner_id)
    
    if request.method == 'POST':
        try:
            # Update partner fields
            partner.name = request.POST.get('name', partner.name)
            partner.contact_person = request.POST.get('contact_person', partner.contact_person)
            partner.phone = request.POST.get('phone', partner.phone)
            partner.email = request.POST.get('email', partner.email)
            partner.address = request.POST.get('address', partner.address)
            partner.status = request.POST.get('status', partner.status)
            
            # Handle numeric fields
            try:
                partner.max_daily_deliveries = int(request.POST.get('max_daily_deliveries', partner.max_daily_deliveries))
                partner.cost_per_delivery = float(request.POST.get('cost_per_delivery', partner.cost_per_delivery))
            except ValueError:
                messages.error(request, 'Invalid number format in max deliveries or cost fields.')
                return render(request, 'delivery/edit_partner.html', {'partner': partner})
            
            # Handle service areas
            service_areas_str = request.POST.get('service_areas', '')
            if service_areas_str:
                service_areas = [area.strip() for area in service_areas_str.split(',') if area.strip()]
                partner.service_areas = service_areas
            
            partner.save()
            
            messages.success(request, f'Delivery partner "{partner.name}" updated successfully!')
            return redirect('delivery:partner_list')
            
        except Exception as e:
            messages.error(request, f'Error updating partner: {str(e)}')
    
    context = {
        'partner': partner,
        'service_areas_str': ', '.join(partner.service_areas) if partner.service_areas else ''
    }
    
    return render(request, 'delivery/edit_partner.html', context)

@login_required
@user_passes_test(is_staff_or_admin)
def create_delivery(request):
    """Manually create a delivery for an order"""
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        
        try:
            order = Order.objects.get(order_id=order_id)
            
            # Check if delivery already exists
            if hasattr(order, 'delivery'):
                messages.error(request, f'Delivery already exists for Order #{order_id}')
                return redirect('delivery:dashboard')
            
            # Create delivery (this will trigger the signal)
            if order.status != 'confirmed':
                order.status = 'confirmed'
                order.save()  # This triggers the signal to create delivery
            
            messages.success(request, f'Delivery created for Order #{order_id}')
            
        except Order.DoesNotExist:
            messages.error(request, f'Order #{order_id} not found')
    
    return redirect('delivery:dashboard')

@login_required
def rate_delivery(request, delivery_id):
    """Rate a completed delivery"""
    if request.method == 'POST':
        delivery = get_object_or_404(
            Delivery, 
            id=delivery_id, 
            order__user=request.user, 
            status='delivered'
        )
        
        rating = request.POST.get('rating')
        feedback = request.POST.get('feedback', '')
        
        if rating and rating.isdigit() and 1 <= int(rating) <= 5:
            delivery.customer_rating = int(rating)
            delivery.customer_feedback = feedback
            delivery.save()
            
            # Update partner's average rating
            if delivery.delivery_partner:
                partner = delivery.delivery_partner
                partner_deliveries = Delivery.objects.filter(
                    delivery_partner=partner,
                    customer_rating__isnull=False
                )
                avg_rating = sum(d.customer_rating for d in partner_deliveries) / partner_deliveries.count()
                partner.rating = round(avg_rating, 2)
                partner.save()
            
            messages.success(request, 'Thank you for your feedback!')
        else:
            messages.error(request, 'Please provide a valid rating (1-5)')
    
    return redirect('delivery:track_delivery', order_id=delivery.order.order_id)

# API Views for real-time updates
@login_required
def delivery_status_api(request, tracking_id):
    """API endpoint to get delivery status"""
    try:
        delivery = Delivery.objects.select_related('order', 'delivery_partner').get(
            tracking_id=tracking_id
        )
        
        # Check if user can access this delivery
        if not (request.user == delivery.order.user or 
                request.user.user_type in ['staff', 'admin']):
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        data = {
            'tracking_id': delivery.tracking_id,
            'status': delivery.status,
            'status_display': delivery.get_status_display(),
            'estimated_delivery': delivery.estimated_delivery_time.isoformat() if delivery.estimated_delivery_time else None,
            'actual_delivery': delivery.actual_delivery_time.isoformat() if delivery.actual_delivery_time else None,
            'partner': delivery.delivery_partner.name if delivery.delivery_partner else None,
            'updates': [
                {
                    'status': update.status,
                    'status_display': update.get_status_display(),
                    'location': update.location,
                    'description': update.description,
                    'timestamp': update.timestamp.isoformat()
                }
                for update in delivery.updates.all()
            ]
        }
        
        return JsonResponse(data)
        
    except Delivery.DoesNotExist:
        return JsonResponse({'error': 'Delivery not found'}, status=404)

@login_required
@user_passes_test(is_staff_or_admin)
def bulk_assign_partners(request):
    """Bulk assign partners to unassigned deliveries"""
    if request.method == 'POST':
        unassigned_deliveries = Delivery.objects.filter(
            delivery_partner__isnull=True,
            status='assigned'
        )
        
        assigned_count = 0
        for delivery in unassigned_deliveries:
            partner = DeliveryPartner.get_default_partner(
                delivery.order.shipping_pincode
            )
            
            if partner:
                delivery.delivery_partner = partner
                delivery.delivery_cost = float(partner.cost_per_delivery) if partner.cost_per_delivery > 0 else delivery.delivery_cost
                delivery.save()
                
                # Create tracking update
                DeliveryUpdate.objects.create(
                    delivery=delivery,
                    status='assigned',
                    description=f"Auto-assigned to {partner.name}"
                )
                
                assigned_count += 1
        
        if assigned_count > 0:
            messages.success(request, f'{assigned_count} deliveries assigned to partners')
        else:
            messages.info(request, 'No deliveries could be auto-assigned. Check partner availability.')
    
    return redirect('delivery:dashboard')