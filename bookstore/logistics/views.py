# logistics/views.py - Enhanced version
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from .models import VendorPickup, LogisticsPartner, PickupTracking, DeliverySchedule, StockReceiptConfirmation, DeliveryTracking
from vendors.models import StockOffer, OfferStatusNotification
from warehouse.models import Stock, StockMovement
from .forms import StockReceiptForm
# logistics/views.py
from .forms import LogisticsPartnerForm

def is_staff_or_admin(user):
    return user.is_authenticated and user.user_type in ['staff', 'admin']

# logistics/views.py - FIXED logistics_dashboard function

@login_required
@user_passes_test(is_staff_or_admin)
def logistics_dashboard(request):
    """FIXED: Dashboard showing both old pickups and new delivery schedules"""
    
    # OLD PICKUP SYSTEM STATS (for backward compatibility)
    scheduled_pickups = VendorPickup.objects.filter(status='scheduled').count()
    in_transit_pickups = VendorPickup.objects.filter(status='in_transit').count()
    completed_pickups = VendorPickup.objects.filter(status='delivered').count()
    
    # NEW DELIVERY SCHEDULE STATS - FIXED QUERIES
    pending_assignments = DeliverySchedule.objects.filter(
        status='scheduled', 
        assigned_partner__isnull=True
    ).count()
    
    assigned_deliveries = DeliverySchedule.objects.filter(
        status__in=['confirmed', 'pickup_assigned'],
        assigned_partner__isnull=False
    ).count()
    
    active_deliveries = DeliverySchedule.objects.filter(
        status__in=['collected', 'in_transit']
    ).count()
    
    pending_confirmations = DeliverySchedule.objects.filter(
        status='arrived'
    ).count()
    
    completed_deliveries = DeliverySchedule.objects.filter(
        status__in=['verified', 'completed']
    ).count()
    
    # FIXED: Recent deliveries needing attention - should show ALL scheduled deliveries
    recent_scheduled_deliveries = DeliverySchedule.objects.filter(
        status='scheduled'
    ).select_related(
        'vendor', 'stock_offer__book', 'vendor_location'
    ).prefetch_related(
        'stock_offer__book__authors'
    ).order_by('-created_at')[:5]
    
    # FIXED: Recent deliveries needing staff confirmation
    pending_receipts = DeliverySchedule.objects.filter(
        status='arrived'
    ).select_related(
        'vendor', 'stock_offer__book', 'assigned_partner'
    ).order_by('actual_delivery_time')[:5]
    
    # Recent pickups (old system)
    recent_pickups = VendorPickup.objects.select_related(
        'vendor', 'logistics_partner', 'stock_offer__book'
    ).order_by('-created_at')[:5]
    
    # All active logistics partners
    active_partners = LogisticsPartner.objects.filter(status='active').count()
    
    # DEBUG: Print actual counts to help troubleshoot
    print(f"DEBUG - Total DeliverySchedule objects: {DeliverySchedule.objects.count()}")
    print(f"DEBUG - Scheduled deliveries: {pending_assignments}")
    print(f"DEBUG - Recent scheduled deliveries: {len(recent_scheduled_deliveries)}")
    
    context = {
        # Old system stats
        'scheduled_pickups': scheduled_pickups,
        'in_transit_pickups': in_transit_pickups,
        'completed_pickups': completed_pickups,
        
        # New delivery system stats - FIXED
        'pending_assignments': pending_assignments,
        'assigned_deliveries': assigned_deliveries,
        'active_deliveries': active_deliveries,
        'pending_confirmations': pending_confirmations,
        'completed_deliveries': completed_deliveries,
        
        'recent_scheduled_deliveries': recent_scheduled_deliveries,
        'pending_receipts': pending_receipts,
        'recent_pickups': recent_pickups,
        'active_partners': active_partners,
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

# NEW VIEWS FOR DELIVERY MANAGEMENT

@login_required
@user_passes_test(is_staff_or_admin)
def delivery_list(request):
    """ENHANCED: List all delivery schedules with better filtering"""
    deliveries_list = DeliverySchedule.objects.select_related(
        'vendor', 'stock_offer__book', 'assigned_partner', 'vendor_location'
    ).prefetch_related('stock_offer__book__authors').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        deliveries_list = deliveries_list.filter(status=status_filter)
    
    # Filter by partner assignment
    partner_filter = request.GET.get('partner')
    if partner_filter == 'unassigned':
        deliveries_list = deliveries_list.filter(assigned_partner__isnull=True)
    elif partner_filter == 'assigned':
        deliveries_list = deliveries_list.filter(assigned_partner__isnull=False)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        deliveries_list = deliveries_list.filter(
            Q(vendor__business_name__icontains=search_query) |
            Q(stock_offer__book__title__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(assigned_partner__name__icontains=search_query)
        )
    
    paginator = Paginator(deliveries_list, 20)
    page_number = request.GET.get('page')
    deliveries = paginator.get_page(page_number)
    
    # Get available logistics partners for assignment
    available_partners = LogisticsPartner.objects.filter(status='active').order_by('name')
    
    # Calculate summary stats
    stats = {
        'total': deliveries_list.count(),
        'scheduled': deliveries_list.filter(status='scheduled').count(),
        'in_progress': deliveries_list.filter(status__in=['confirmed', 'pickup_assigned', 'collected', 'in_transit']).count(),
        'completed': deliveries_list.filter(status='completed').count(),
        'need_assignment': deliveries_list.filter(status='scheduled', assigned_partner__isnull=True).count(),
    }
    
    context = {
        'deliveries': deliveries,
        'status_filter': status_filter,
        'partner_filter': partner_filter,
        'search_query': search_query,
        'available_partners': available_partners,
        'stats': stats,
    }
    
    return render(request, 'logistics/delivery_list.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def delivery_detail(request, delivery_id):
    """Detailed view of a delivery schedule"""
    delivery = get_object_or_404(
        DeliverySchedule.objects.select_related(
            'vendor', 'stock_offer__book', 'assigned_partner', 'vendor_location'
        ).prefetch_related('stock_offer__book__authors'),
        id=delivery_id
    )
    tracking_updates = delivery.tracking_updates.all().order_by('-timestamp')
    
    # Get available logistics partners for potential assignment/reassignment
    available_partners = LogisticsPartner.objects.filter(status='active').order_by('name')
    
    context = {
        'delivery': delivery,
        'tracking_updates': tracking_updates,
        'available_partners': available_partners,
    }
    
    return render(request, 'logistics/delivery_detail.html', context)


@login_required
@user_passes_test(is_staff_or_admin)
def pending_receipts(request):
    """List deliveries that have arrived and need staff confirmation"""
    pending_list = DeliverySchedule.objects.filter(
        status='arrived'
    ).select_related('vendor', 'stock_offer__book', 'assigned_partner').order_by('actual_delivery_time')
    
    context = {
        'pending_receipts': pending_list,
    }
    
    return render(request, 'logistics/pending_receipts.html', context)

# Replace the confirm_stock_receipt function in views.py with this fixed version:

@login_required
@user_passes_test(is_staff_or_admin)
def confirm_stock_receipt(request, delivery_id):
    """Staff confirms delivery and updates stock automatically - FIXED VERSION"""
    delivery = get_object_or_404(DeliverySchedule, id=delivery_id)
    
    # Check if confirmation already exists
    existing_confirmation = StockReceiptConfirmation.objects.filter(
        delivery_schedule=delivery
    ).first()
    
    if existing_confirmation:
        messages.warning(
            request, 
            f'This delivery has already been confirmed on {existing_confirmation.confirmed_at.strftime("%B %d, %Y at %I:%M %p")} by {existing_confirmation.received_by_staff.get_full_name() or existing_confirmation.received_by_staff.username}.'
        )
        return redirect('logistics:delivery_detail', delivery_id=delivery_id)
    
    if delivery.status != 'arrived':
        messages.error(request, 'This delivery is not ready for confirmation.')
        return redirect('logistics:delivery_detail', delivery_id=delivery_id)
    
    if request.method == 'POST':
        form = StockReceiptForm(request.POST, request.FILES)
        if form.is_valid():
            confirmation = form.save(commit=False)
            confirmation.delivery_schedule = delivery
            confirmation.received_by_staff = request.user
            confirmation.save()
            
            # Auto-update stock if books accepted
            if confirmation.books_accepted > 0:
                try:
                    # Get or create stock record for this book
                    stock, created = Stock.objects.get_or_create(
                        book=delivery.stock_offer.book,
                        defaults={
                            'quantity': 0,
                            'reserved_quantity': 0,
                            'reorder_level': 10,
                            'max_stock_level': 100
                        }
                    )
                    
                    # Create stock movement record FIRST
                    movement = StockMovement.objects.create(
                        stock=stock,
                        movement_type='in',
                        quantity=confirmation.books_accepted,
                        reference=f"Delivery-{delivery.id}",
                        reason=f"Vendor delivery from {delivery.vendor.business_name}",
                        performed_by=request.user,
                    )
                    
                    # FIXED: Only update quantity, let available_quantity be calculated by property
                    stock.quantity += confirmation.books_accepted
                    stock.save()
                    
                    # Mark confirmation as completed
                    confirmation.stock_updated = True
                    confirmation.stock_movement_created = True
                    confirmation.save()
                    
                    # FIXED: Update delivery status to 'verified' first, then 'completed'
                    delivery.status = 'verified'
                    delivery.verified_quantity = confirmation.books_accepted
                    delivery.save()
                    
                    # Create tracking update for verification
                    DeliveryTracking.objects.create(
                        delivery=delivery,
                        status='verified',
                        notes=f"Stock verified by {request.user.get_full_name() or request.user.username}. {confirmation.books_accepted} books accepted.",
                        updated_by=request.user
                    )
                    
                    # Now mark as completed
                    delivery.status = 'completed'
                    delivery.completed_at = timezone.now()
                    delivery.save()
                    
                    # Create final tracking update
                    DeliveryTracking.objects.create(
                        delivery=delivery,
                        status='completed',
                        notes=f"Stock receipt confirmed. {confirmation.books_accepted} books added to inventory.",
                        updated_by=request.user
                    )
                    
                    # Update original stock offer
                    delivery.stock_offer.status = 'processed'
                    delivery.stock_offer.is_delivered = True
                    delivery.stock_offer.delivered_at = timezone.now()
                    delivery.stock_offer.delivered_quantity = confirmation.books_accepted
                    delivery.stock_offer.staff_confirmed_by = request.user
                    delivery.stock_offer.staff_confirmed_at = timezone.now()
                    delivery.stock_offer.save()
                    
                    # Create notification for vendor
                    OfferStatusNotification.objects.create(
                        stock_offer=delivery.stock_offer,
                        status='completed',
                        message=f"Stock confirmed! {confirmation.books_accepted} copies of '{delivery.stock_offer.book.title}' have been added to our inventory. Your offer is now complete."
                    )
                    
                    messages.success(
                        request, 
                        f'Stock receipt confirmed! {confirmation.books_accepted} books added to inventory. '
                        f'Stock movement #{movement.id} created. Delivery status updated to completed.'
                    )
                    
                except Exception as e:
                    messages.error(request, f'Error updating stock: {str(e)}')
                    # Clean up the confirmation if stock update failed
                    confirmation.delete()
                    return render(request, 'logistics/confirm_receipt.html', {
                        'form': form, 'delivery': delivery
                    })
            else:
                # No books accepted - mark delivery as completed but don't update stock
                delivery.status = 'completed'
                delivery.verified_quantity = 0
                delivery.completed_at = timezone.now()
                delivery.save()
                
                # Create tracking update
                DeliveryTracking.objects.create(
                    delivery=delivery,
                    status='completed',
                    notes=f"No books accepted. Reason: {confirmation.rejection_reason or 'Quality issues'}",
                    updated_by=request.user
                )
                
                # Update stock offer status
                delivery.stock_offer.status = 'rejected'
                delivery.stock_offer.staff_confirmed_by = request.user
                delivery.stock_offer.staff_confirmed_at = timezone.now()
                delivery.stock_offer.save()
                
                # Create notification
                OfferStatusNotification.objects.create(
                    stock_offer=delivery.stock_offer,
                    status='rejected',
                    message=f"Unfortunately, no books were accepted from your delivery. Reason: {confirmation.rejection_reason or 'Quality issues'}"
                )
                
                messages.warning(request, 'No books were accepted from this delivery. Delivery marked as completed.')
            
            # FIXED: Redirect to pending_receipts so the list refreshes
            return redirect('logistics:pending_receipts')
        else:
            # Form has errors - display them
            messages.error(request, 'Please correct the errors below.')
    else:
        # Pre-fill form with delivery quantity
        initial_data = {
            'books_received': delivery.stock_offer.quantity,
            'books_accepted': delivery.stock_offer.quantity,
        }
        form = StockReceiptForm(initial=initial_data)
    
    context = {
        'form': form, 
        'delivery': delivery,
        'stock_offer': delivery.stock_offer,
    }
    
    return render(request, 'logistics/confirm_receipt.html', context)
@login_required
@user_passes_test(is_staff_or_admin)
def update_delivery_status(request, delivery_id):
    """ENHANCED: Update delivery status with better tracking"""
    delivery = get_object_or_404(DeliverySchedule, id=delivery_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        location = request.POST.get('location', '')
        notes = request.POST.get('notes', '')
        
        if new_status and new_status in dict(DeliverySchedule.DELIVERY_STATUS):
            old_status = delivery.status
            delivery.status = new_status
            
            # Set appropriate timestamps
            now = timezone.now()
            if new_status == 'confirmed' and not delivery.confirmed_at:
                delivery.confirmed_at = now
            elif new_status == 'collected' and not delivery.actual_pickup_time:
                delivery.actual_pickup_time = now
            elif new_status == 'arrived' and not delivery.actual_delivery_time:
                delivery.actual_delivery_time = now
            
            delivery.save()
            
            # Create tracking update
            tracking_notes = notes or f"Status updated from {old_status} to {new_status}"
            if location:
                tracking_notes += f" at {location}"
                
            DeliveryTracking.objects.create(
                delivery=delivery,
                status=new_status,
                location=location,
                notes=tracking_notes,
                updated_by=request.user
            )
            
            # Send vendor notifications for key status changes
            vendor_notifications = {
                'confirmed': 'Your delivery has been confirmed by our logistics team.',
                'collected': 'Your books have been picked up and are on the way to our warehouse.',
                'in_transit': 'Your delivery is in transit to our warehouse.',
                'arrived': 'Your books have arrived at our warehouse and are being processed.'
            }
            
            if new_status in vendor_notifications:
                OfferStatusNotification.objects.create(
                    stock_offer=delivery.stock_offer,
                    status=new_status,
                    message=vendor_notifications[new_status]
                )
            
            messages.success(request, f'Delivery status updated to {delivery.get_status_display()}')
        else:
            messages.error(request, 'Invalid status selected.')
    
    return redirect('logistics:delivery_detail', delivery_id=delivery_id)


@login_required
@user_passes_test(is_staff_or_admin)
def assign_logistics_partner(request, delivery_id):
    """ENHANCED: Assign a logistics partner to a delivery"""
    delivery = get_object_or_404(DeliverySchedule, id=delivery_id)
    
    if request.method == 'POST':
        partner_id = request.POST.get('partner_id')
        notes = request.POST.get('notes', '')
        
        if partner_id:
            try:
                partner = LogisticsPartner.objects.get(id=partner_id, status='active')
                
                # Update delivery
                old_partner = delivery.assigned_partner
                delivery.assigned_partner = partner
                delivery.status = 'pickup_assigned'
                delivery.save()
                
                # Create tracking update
                if old_partner:
                    tracking_message = f"Logistics partner reassigned from {old_partner.name} to {partner.name}"
                else:
                    tracking_message = f"Logistics partner assigned: {partner.name}"
                
                if notes:
                    tracking_message += f". Notes: {notes}"
                
                DeliveryTracking.objects.create(
                    delivery=delivery,
                    status='pickup_assigned',
                    notes=tracking_message,
                    updated_by=request.user
                )
                
                # Notify vendor
                OfferStatusNotification.objects.create(
                    stock_offer=delivery.stock_offer,
                    status='pickup_assigned',
                    message=f"Logistics partner {partner.name} has been assigned to your delivery. They will contact you at {delivery.contact_phone} to arrange pickup."
                )
                
                messages.success(request, f'Logistics partner {partner.name} assigned successfully!')
                
            except LogisticsPartner.DoesNotExist:
                messages.error(request, 'Selected logistics partner not found or inactive.')
        else:
            messages.error(request, 'Please select a logistics partner.')
    
    return redirect('logistics:delivery_detail', delivery_id=delivery_id)



@login_required
@user_passes_test(is_staff_or_admin)
def logistics_partner_list(request):
    """List all logistics partners"""
    partners = LogisticsPartner.objects.all().order_by('name')
    return render(request, 'logistics/partner_list.html', {'partners': partners})

@login_required
@user_passes_test(is_staff_or_admin)
def logistics_partner_create(request):
    """Create a new logistics partner"""
    if request.method == 'POST':
        form = LogisticsPartnerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Logistics Partner created successfully.")
            return redirect('logistics:partner_list')
    else:
        form = LogisticsPartnerForm()
    return render(request, 'logistics/partner_form.html', {'form': form})

@login_required
@user_passes_test(is_staff_or_admin)
def logistics_partner_edit(request, partner_id):
    """Edit an existing logistics partner"""
    partner = get_object_or_404(LogisticsPartner, id=partner_id)
    if request.method == 'POST':
        form = LogisticsPartnerForm(request.POST, instance=partner)
        if form.is_valid():
            form.save()
            messages.success(request, "Logistics Partner updated successfully.")
            return redirect('logistics:partner_list')
    else:
        form = LogisticsPartnerForm(instance=partner)
    return render(request, 'logistics/partner_form.html', {'form': form, 'partner': partner})
