# logistics/views.py - Enhanced version
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import VendorPickup, LogisticsPartner, PickupTracking, DeliverySchedule, StockReceiptConfirmation
from vendors.models import StockOffer, OfferStatusNotification
from warehouse.models import Stock, StockMovement
from .forms import StockReceiptForm

def is_staff_or_admin(user):
    return user.is_authenticated and user.user_type in ['staff', 'admin']

@login_required
@user_passes_test(is_staff_or_admin)
def logistics_dashboard(request):
    # Enhanced dashboard with delivery schedules
    scheduled_pickups = VendorPickup.objects.filter(status='scheduled').count()
    in_transit_pickups = VendorPickup.objects.filter(status='in_transit').count()
    completed_pickups = VendorPickup.objects.filter(status='delivered').count()
    
    # Delivery schedules awaiting confirmation
    pending_confirmations = DeliverySchedule.objects.filter(status='arrived').count()
    
    recent_pickups = VendorPickup.objects.select_related(
        'vendor', 'logistics_partner', 'stock_offer__book'
    ).order_by('-created_at')[:10]
    
    # Recent deliveries needing staff confirmation
    pending_receipts = DeliverySchedule.objects.filter(
        status='arrived'
    ).select_related('vendor', 'stock_offer__book')[:5]
    
    context = {
        'scheduled_pickups': scheduled_pickups,
        'in_transit_pickups': in_transit_pickups,
        'completed_pickups': completed_pickups,
        'pending_confirmations': pending_confirmations,
        'recent_pickups': recent_pickups,
        'pending_receipts': pending_receipts,
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
    """List all delivery schedules"""
    deliveries_list = DeliverySchedule.objects.select_related(
        'vendor', 'stock_offer__book', 'assigned_partner'
    ).order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        deliveries_list = deliveries_list.filter(status=status_filter)
    
    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        deliveries_list = deliveries_list.filter(
            Q(vendor__business_name__icontains=search_query) |
            Q(stock_offer__book__title__icontains=search_query) |
            Q(contact_person__icontains=search_query)
        )
    
    paginator = Paginator(deliveries_list, 20)
    page_number = request.GET.get('page')
    deliveries = paginator.get_page(page_number)
    
    context = {
        'deliveries': deliveries,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'logistics/delivery_list.html', context)

@login_required
@user_passes_test(is_staff_or_admin)
def delivery_detail(request, delivery_id):
    """Detailed view of a delivery schedule"""
    delivery = get_object_or_404(DeliverySchedule, id=delivery_id)
    tracking_updates = delivery.tracking_updates.all().order_by('-timestamp')
    
    context = {
        'delivery': delivery,
        'tracking_updates': tracking_updates,
    }
    
    return render(request, 'logistics/delivery_detail.html', context)

@login_required
@user_passes_test(is_staff_or_admin)
def pending_receipts(request):
    """List deliveries that have arrived and need staff confirmation"""
    pending_list = DeliverySchedule.objects.filter(
        status='arrived'
    ).select_related('vendor', 'stock_offer__book').order_by('actual_delivery_time')
    
    context = {
        'pending_receipts': pending_list,
    }
    
    return render(request, 'logistics/pending_receipts.html', context)

@login_required
@user_passes_test(is_staff_or_admin)
def confirm_stock_receipt(request, delivery_id):
    """Staff confirms delivery and updates stock automatically"""
    delivery = get_object_or_404(DeliverySchedule, id=delivery_id)
    
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
                            'reorder_level': 10,
                            'max_stock_level': 100
                        }
                    )
                    
                    # Create stock movement record
                    movement = StockMovement.objects.create(
                        stock=stock,
                        movement_type='in',
                        quantity=confirmation.books_accepted,
                        reference=f"Delivery-{delivery.id}",
                        reason=f"Vendor delivery from {delivery.vendor.business_name}",
                        performed_by=request.user,
                    )
                    
                    # Update stock quantity
                    stock.quantity += confirmation.books_accepted
                    stock.save()
                    
                    # Mark confirmation as completed
                    confirmation.stock_updated = True
                    confirmation.stock_movement_created = True
                    confirmation.save()
                    
                    # Update delivery status
                    delivery.status = 'completed'
                    delivery.verified_quantity = confirmation.books_accepted
                    delivery.save()
                    
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
                        status='confirmed',
                        message=f"Stock confirmed! {confirmation.books_accepted} copies of '{delivery.stock_offer.book.title}' added to inventory."
                    )
                    
                    messages.success(
                        request, 
                        f'Stock receipt confirmed! {confirmation.books_accepted} books added to inventory. Stock movement #{movement.id} created.'
                    )
                    
                except Exception as e:
                    messages.error(request, f'Error updating stock: {str(e)}')
                    return render(request, 'logistics/confirm_receipt.html', {
                        'form': form, 'delivery': delivery
                    })
            else:
                # No books accepted - mark delivery as completed but don't update stock
                delivery.status = 'completed'
                delivery.verified_quantity = 0
                delivery.save()
                
                messages.warning(request, 'No books were accepted from this delivery.')
            
            return redirect('logistics:pending_receipts')
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
    """Update delivery status and add tracking information"""
    delivery = get_object_or_404(DeliverySchedule, id=delivery_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        location = request.POST.get('location', '')
        notes = request.POST.get('notes', '')
        
        if new_status and new_status in dict(DeliverySchedule.DELIVERY_STATUS):
            # Update delivery status
            old_status = delivery.status
            delivery.status = new_status
            
            # Set timestamp for specific statuses
            if new_status == 'collected':
                delivery.actual_pickup_time = timezone.now()
            elif new_status == 'arrived':
                delivery.actual_delivery_time = timezone.now()
            
            delivery.save()
            
            # Create tracking update
            DeliveryTracking.objects.create(
                delivery=delivery,
                status=new_status,
                location=location,
                notes=notes or f"Status updated from {old_status} to {new_status}",
                updated_by=request.user
            )
            
            # Notify vendor of important status changes
            if new_status in ['collected', 'in_transit', 'arrived']:
                status_messages = {
                    'collected': 'Your books have been picked up and are on the way!',
                    'in_transit': 'Your delivery is in transit to our warehouse.',
                    'arrived': 'Your books have arrived at our warehouse and are being processed.'
                }
                
                OfferStatusNotification.objects.create(
                    stock_offer=delivery.stock_offer,
                    status=new_status,
                    message=status_messages.get(new_status, f"Delivery status updated to {delivery.get_status_display()}")
                )
            
            messages.success(request, f'Delivery status updated to {delivery.get_status_display()}')
        else:
            messages.error(request, 'Invalid status selected.')
    
    return redirect('logistics:delivery_detail', delivery_id=delivery_id)

@login_required
@user_passes_test(is_staff_or_admin)
def assign_logistics_partner(request, delivery_id):
    """Assign a logistics partner to a delivery"""
    delivery = get_object_or_404(DeliverySchedule, id=delivery_id)
    
    if request.method == 'POST':
        partner_id = request.POST.get('partner_id')
        if partner_id:
            try:
                partner = LogisticsPartner.objects.get(id=partner_id, status='active')
                delivery.assigned_partner = partner
                delivery.status = 'pickup_assigned'
                delivery.save()
                
                # Create tracking update
                DeliveryTracking.objects.create(
                    delivery=delivery,
                    status='pickup_assigned',
                    notes=f"Assigned to logistics partner: {partner.name}",
                    updated_by=request.user
                )
                
                messages.success(request, f'Logistics partner {partner.name} assigned to delivery.')
            except LogisticsPartner.DoesNotExist:
                messages.error(request, 'Selected logistics partner not found or inactive.')
    
    return redirect('logistics:delivery_detail', delivery_id=delivery_id)